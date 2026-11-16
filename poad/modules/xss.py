"""Cross-Site Scripting module.

Context-aware (HTML body, attribute, JS string, URL, SVG). Payloads carry a
user-chosen proof marker and benign alert() PoCs. A payload reflected in a
response does not by itself prove executable XSS.
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

CONTEXTS = ("html", "html-attribute", "js-string", "url", "svg", "unknown")
QUOTES = ("any", "double", "single", "none")


class XSSModule(BaseModule):
    key = "xss"
    aliases = ("cross-site-scripting",)
    title = "Cross-Site Scripting"
    summary = "Context-appropriate reflected-XSS probes with a proof marker."

    def options(self) -> list[Option]:
        return [
            Option("context", "Injection context", type="choice", choices=CONTEXTS,
                   default="unknown", prompt="Injection context"),
            Option("quote", "Attribute/JS quote style", type="choice", choices=QUOTES,
                   default="any", prompt="Quote style"),
            Option("marker",
                   "Unique string to look for in the response (proof of reflection)",
                   default="POAD", prompt="Marker", example="POAD7391"),
        ]

    def build(self, ctx: dict[str, Any], library) -> BuildOutput:
        ctx = self.apply_defaults(ctx)
        context = str(ctx.get("context", "unknown")).lower()
        quote = str(ctx.get("quote", "any")).lower()
        marker = str(ctx.get("marker") or "POAD")
        if context not in CONTEXTS:
            raise ModuleError(f"context must be one of: {', '.join(CONTEXTS)}")
        if quote not in QUOTES:
            raise ModuleError(f"quote must be one of: {', '.join(QUOTES)}")

        templates = library.by_category("xss")
        context_filter = None if context == "unknown" else {context}
        selected = select_templates(templates, context=context_filter)

        if quote != "any":
            wanted = {f"quote:{quote}"}
            selected = [
                t
                for t in selected
                if not any(tag.startswith("quote:") for tag in t.tags)
                or wanted & set(t.tags)
            ]

        units: list[Unit] = []
        for t in selected:
            rendered = template_engine.substitute(t.template, {"MARKER": marker})
            units.append(
                Unit(
                    value=rendered,
                    transforms=(),
                    family=f"{t.context}:{t.mode}",
                    template_id=t.id,
                    note=t.notes,
                )
            )
        if not units:
            raise ModuleError(
                f"No XSS templates for context={context}, quote={quote}."
            )

        notes = [
            "Marker-tagged payloads let you grep responses for reflection; "
            "reflection is necessary but not sufficient for executable XSS.",
            "alert() is a benign proof of concept. Encoding is left raw so Burp "
            "can apply the encoding appropriate to the sink.",
        ]
        info = {"Category": "Cross-Site Scripting", "Context": context,
                "Quote": quote, "Marker": marker}
        return BuildOutput(units=units, info=info, notes=notes)


register(XSSModule())
