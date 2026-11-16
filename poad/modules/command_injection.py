"""Command Injection module.

OS- and shell-aware command separators with a user-supplied *harmless*
diagnostic command (default: ``id`` on Linux, ``whoami`` on Windows). The default
library contains no reverse shells, persistence, destructive commands, or
network callbacks.
"""

from __future__ import annotations

from typing import Any

from poad.core import template_engine
from poad.core.generator import Unit
from poad.modules.base import (
    BaseModule,
    BuildOutput,
    ModuleError,
    Option,
    register,
    select_templates,
)

OSES = ("linux", "windows")
SHELLS = ("any", "unix", "unix-quoted", "cmd", "powershell")
_DEFAULT_CMD = {"linux": "id", "windows": "whoami"}


class CommandInjectionModule(BaseModule):
    key = "cmdi"
    aliases = ("command-injection", "command_injection", "cmd")
    title = "Command Injection"
    summary = "OS/shell-aware command separators with a harmless test command."

    def options(self) -> list[Option]:
        return [
            Option("os", "Target operating system", type="choice", choices=OSES,
                   default="linux", prompt="Target OS"),
            Option("shell", "Shell context", type="choice", choices=SHELLS,
                   default="any", prompt="Shell context"),
            Option("command", "Harmless diagnostic command to inject",
                   prompt="Test command (blank = default)", example="id"),
        ]

    def build(self, ctx: dict[str, Any], library) -> BuildOutput:
        ctx = self.apply_defaults(ctx)
        os_name = str(ctx.get("os", "linux")).lower()
        shell = str(ctx.get("shell", "any")).lower()
        if os_name not in OSES:
            raise ModuleError(f"os must be one of: {', '.join(OSES)}")
        if shell not in SHELLS:
            raise ModuleError(f"shell must be one of: {', '.join(SHELLS)}")

        command = str(ctx.get("command") or _DEFAULT_CMD[os_name]).strip()
        if not command:
            raise ModuleError("command must not be empty")
        if "\n" in command or "\r" in command:
            raise ModuleError("command must be a single line")

        templates = library.by_category("command_injection")
        platform_filter = {os_name}
        context_filter = None if shell == "any" else {shell}
        selected = select_templates(
            templates, platform=platform_filter, context=context_filter
        )

        units: list[Unit] = []
        for t in selected:
            rendered = template_engine.substitute(t.template, {"COMMAND": command})
            units.append(
                Unit(
                    value=rendered,
                    transforms=(),
                    family=f"{t.platform}:{t.context}",
                    template_id=t.id,
                    note=t.notes,
                )
            )
        if not units:
            raise ModuleError(f"No command-injection templates for os={os_name}, shell={shell}.")

        notes = [
            "Not every injection point invokes the same shell; try multiple "
            "separators. The default command only prints identity/marker output.",
            f"Default test command for {os_name}: {_DEFAULT_CMD[os_name]!r}.",
        ]
        info = {"Category": "Command Injection", "OS": os_name, "Shell": shell,
                "Command": command}
        return BuildOutput(units=units, info=info, notes=notes)


register(CommandInjectionModule())
