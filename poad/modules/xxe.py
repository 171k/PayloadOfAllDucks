"""XML External Entity module.

XXE payloads are whole XML documents. POAD emits them as single-line XML so they
are valid wordlist entries, but they are flagged whole-document: you replace the
entire request body with one of these, rather than placing it in a single Burp
Sniper marker inside an existing XML value.
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

MODES = ("detection", "file-read")


class XXEModule(BaseModule):
    key = "xxe"
    aliases = ("xml-external-entity",)
    title = "XML External Entity"
    summary = "Whole-document XXE probes (detection and file read)."

    def options(self) -> list[Option]:
        return [
            Option("mode", "Objective", type="choice", choices=MODES,
                   default="detection", prompt="Mode"),
            Option("file", "File to read (file-read mode)", prompt="Target file",
                   example="/flag/flag.txt",
                   gate_field="mode", gate_value="file-read"),
            Option("marker",
                   "Unique string to look for in the response (proof it rendered)",
                   default="POAD", prompt="Marker", example="POAD7391"),
        ]

    def build(self, ctx: dict[str, Any], library) -> BuildOutput:
        ctx = self.apply_defaults(ctx)
        mode = str(ctx.get("mode", "detection")).lower()
        if mode not in MODES:
            raise ModuleError(f"mode must be one of: {', '.join(MODES)}")
        marker = str(ctx.get("marker") or "POAD")
        file_path = ctx.get("file")

        selected = select_templates(library.by_category("xxe"), mode={mode})
        units: list[Unit] = []
        for t in selected:
            values: dict[str, str] = {}
            if "FILE" in t.tokens():
                if not file_path:
                    raise ModuleError(f"Template {t.id!r} needs --file (file-read mode).")
                values["FILE"] = str(file_path)
            if "MARKER" in t.tokens():
                values["MARKER"] = marker
            rendered = template_engine.substitute(t.template, values)
            note = t.notes or ""
            if t.whole_document:
                note = (note + " " if note else "") + "[whole-document: replace the full XML body]"
            units.append(
                Unit(value=rendered, transforms=(), family=f"xxe:{mode}",
                     template_id=t.id, note=note.strip() or None)
            )
        if not units:
            raise ModuleError(f"No XXE templates for mode={mode}.")

        notes = [
            "Each payload is a COMPLETE XML document. Replace the entire request "
            "body with it; do not drop it into a single in-value Sniper marker.",
            "Blind/OOB XXE needs an external collaborator server, which POAD does "
            "not generate by default.",
        ]
        info = {"Category": "XML External Entity", "Mode": mode}
        if file_path:
            info["Target file"] = file_path
        return BuildOutput(units=units, info=info, notes=notes)


register(XXEModule())
