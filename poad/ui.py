"""Terminal presentation helpers.

Rich is used when available and enabled, but every function degrades to plain
``print`` so the tool works in a minimal terminal or when piped. Nothing here is
required for payload generation -- it is presentation only.
"""

from __future__ import annotations

import sys

try:  # optional dependency
    from rich.console import Console as _RichConsole  # type: ignore
    _HAVE_RICH = True
except Exception:  # pragma: no cover - rich not installed
    _RichConsole = None
    _HAVE_RICH = False


_BANNER_UNICODE = """\
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣠⣤⣤⣤⣤⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡤⠞⠋⠁⠀⠀⠀⠀⠀⠀⠉⠙⠲⣄⡀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⡴⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣄⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢀⡞⠁⣀⣀⣀⠀⠀⠀⠀⠀⣀⣠⣤⣤⣤⣤⣄⡀⠘⡆⠀⠀
⠀⠀⠀⠀⢰⣿⣿⣿⣿⠉⠉⠉⣹⡆⠀⠀⣿⣿⣿⣿⡇⠀⢀⣀⡿⠀⢹⠀⠀
⠀⢀⣀⣠⡬⠿⠿⠟⠓⠚⠛⠉⠉⠉⠙⢲⡈⠉⠉⠉⠉⠉⠉⠀⠀⠀⢸⡆⠀
⣞⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢳⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀
⠉⠓⠶⠶⣶⠶⠶⠶⠖⠒⠒⠒⠒⠒⢦⠀⣸⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀
⠀⠀⠀⠀⠈⠓⠒⠶⠶⠶⠶⠶⡶⠶⠖⠚⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⡇⠀  P A Y L O A D   O F   A L L   D U C K S
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣇⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⣄
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈
⠀⠀⠀⠀⠀⠀⠀⢀⡠⠞⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                               ▐■
                               ██
▀▄▓▓▓▄   ▄▓▓▓▓▄   ▄▓▓▄ █▄  ▄▓▄ █▒
░▒▀ ▀▒░ ░▒▀  ▀▒░ ░▒▀  ▀▒░ ░▒▀ ▀▒░
▄▄   ▄▄ ▄▄    ▄▄ ▄▄    ▄▀ ▄▄   ▄▀
▓░▒▄▒░▀ ▀░▒▄▄▒░▀ ▀░▒▄ ▄░▒ ▀░▒▄▄░▒
▓▒▀▀▀▀    ▀▀▀▀     ▀▀▀  ▀   ▀▀  ▀
░▒
▀█"""

_BANNER_ASCII = """\
+--------------------------------------------+
|            PAYLOAD OF ALL DUCKS            |
+--------------------------------------------+"""


def supports_unicode() -> bool:
    enc = getattr(sys.stdout, "encoding", None) or ""
    try:
        "🦆".encode(enc)
        return True
    except (LookupError, UnicodeEncodeError, TypeError):
        return False


def banner(*, unicode: bool = True) -> str:
    return _BANNER_UNICODE if (unicode and supports_unicode()) else _BANNER_ASCII


class Console:
    """Thin wrapper over rich.Console (if available) or plain print."""

    def __init__(self, *, use_rich: bool = True, color: bool = True) -> None:
        self.use_rich = bool(use_rich and _HAVE_RICH and sys.stdout.isatty())
        self._rich = _RichConsole() if self.use_rich else None

    def print(self, *args, style: str | None = None, **kwargs) -> None:
        if self._rich is not None:
            text = " ".join(str(a) for a in args)
            self._rich.print(text, style=style)
        else:
            print(*args, **kwargs)

    def rule(self, title: str = "") -> None:
        if self._rich is not None:
            self._rich.rule(title)
        else:
            line = "-" * 48
            print(f"{line}\n{title}" if title else line)

    def error(self, message: str) -> None:
        if self._rich is not None:
            self._rich.print(f"[bold red]error:[/] {message}")
        else:
            print(f"error: {message}", file=sys.stderr)

    def warn(self, message: str) -> None:
        if self._rich is not None:
            self._rich.print(f"[yellow]warning:[/] {message}")
        else:
            print(f"warning: {message}", file=sys.stderr)

    def success(self, message: str) -> None:
        if self._rich is not None:
            self._rich.print(f"[bold green]{message}[/]")
        else:
            print(message)
