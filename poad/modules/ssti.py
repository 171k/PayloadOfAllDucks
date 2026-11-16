"""Server-Side Template Injection module.

Engine-aware: selecting Jinja2 + detection yields only Jinja2 detection probes,
never FreeMarker/ERB/etc. SSTI payloads are emitted *raw* (no encoding
transforms) because URL/HTML encoding breaks template syntax.
"""

from __future__ import annotations

from typing import Any

from poad.core import template_engine
from poad.core.generator import Unit
from poad.modules.base import BaseModule, BuildOutput, ModuleError, Option, register

MODES = ("detection", "identification", "context", "file-read")


class SSTIModule(BaseModule):
    key = "ssti"
    aliases = ("template-injection",)
    title = "Server-Side Template Injection"
    summary = "Engine-specific SSTI detection/identification/file-read probes."

    def options(self) -> list[Option]:
        return [
            Option("engine", "Template engine", type="choice", required=True,
                   prompt="Template engine"),
            Option("mode", "Objective", type="choice", choices=MODES,
                   default="detection", prompt="Mode"),
            Option("file", "File to read (file-read mode only)",
                   prompt="Target file", example="/flag/flag.txt",
                   gate_field="mode", gate_value="file-read"),
            Option("marker",
                   "Unique string to look for in the response (proves the payload ran)",
                   default="POAD", prompt="Marker", example="POAD7391"),
        ]

    def engines(self, library) -> list[str]:
        engines = {
            t.engine for t in library.by_category("ssti") if t.engine
        }
        return sorted(engines)

    def build(self, ctx: dict[str, Any], library) -> BuildOutput:
        ctx = self.apply_defaults(ctx)
        self.require(ctx, "engine")
        engine = str(ctx["engine"]).lower()
        mode = str(ctx.get("mode", "detection")).lower()
        if mode not in MODES:
            raise ModuleError(f"mode must be one of: {', '.join(MODES)}")

        available_engines = self.engines(library)
        if engine not in available_engines:
            raise ModuleError(
                f"Unknown SSTI engine {engine!r}. "
                f"Available: {', '.join(available_engines)}"
            )

        marker = str(ctx.get("marker") or "POAD")
        file_path = ctx.get("file")

        candidates = [
            t
            for t in library.by_category("ssti")
            if t.engine == engine and (t.mode == mode)
        ]

        warnings: list[str] = []
        notes: list[str] = []
        units: list[Unit] = []

        if not candidates:
            # Honest limitation reporting rather than fabricated payloads.
            msg = (
                f"No builtin {engine} templates for mode {mode!r}. "
            )
            if mode == "file-read":
                msg += (
                    "This engine may not support file reads through ordinary "
                    "template syntax."
                )
            raise ModuleError(msg)

        for tpl in candidates:
            values: dict[str, str] = {}
            if "FILE" in tpl.tokens():
                if not file_path:
                    raise ModuleError(
                        f"Template {tpl.id!r} needs --file (file-read mode)."
                    )
                values["FILE"] = str(file_path)
            if "MARKER" in tpl.tokens():
                values["MARKER"] = marker

            try:
                rendered = template_engine.substitute(tpl.template, values)
            except template_engine.TemplateError as exc:
                raise ModuleError(str(exc)) from exc

            note = tpl.notes
            if tpl.expected:
                note = (note + " " if note else "") + f"[expected: {tpl.expected}]"
            if tpl.version_dependent:
                note = (note + " " if note else "") + "[version/environment dependent]"

            units.append(
                Unit(
                    value=rendered,
                    transforms=(),  # raw only: encoding breaks SSTI syntax
                    family=f"{engine}:{mode}",
                    template_id=tpl.id,
                    note=note,
                )
            )

        notes.append(
            "SSTI payloads are emitted raw. In Burp, use 'Raw payloads' (no extra "
            "URL-encoding) or template braces/quotes will be corrupted."
        )
        if mode == "file-read":
            notes.append(
                "File-read templates are environment-dependent; some engines cannot "
                "read arbitrary files via template syntax at all."
            )

        info = {
            "Category": "Server-Side Template Injection",
            "Engine": engine,
            "Mode": mode,
        }
        if file_path:
            info["Target file"] = file_path
        return BuildOutput(units=units, info=info, warnings=warnings, notes=notes)


register(SSTIModule())
