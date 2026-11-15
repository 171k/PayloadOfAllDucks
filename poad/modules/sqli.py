"""SQL Injection module.

Context- and DBMS-aware. Selecting MySQL does not mix in PostgreSQL/MSSQL
dialect-specific payloads (generic probes are always included). Only
non-destructive diagnostic payloads are shipped -- no DROP/DELETE/UPDATE.
"""

from __future__ import annotations

from typing import Any

from poad.core.generator import Unit
from poad.modules.base import (
    BaseModule,
    BuildOutput,
    ModuleError,
    Option,
    register,
    select_templates,
)

DBMS = ("mysql", "postgres", "sqlite", "mssql", "generic")
CONTEXTS = ("string", "numeric", "search", "unknown")
MODES = ("detection", "boolean", "error", "union")


class SQLiModule(BaseModule):
    key = "sqli"
    aliases = ("sql-injection", "sql")
    title = "SQL Injection"
    summary = "Non-destructive, context-aware SQL injection diagnostic probes."

    def options(self) -> list[Option]:
        return [
            Option("dbms", "Target database engine", type="choice", choices=DBMS,
                   default="generic", prompt="Database engine"),
            Option("context", "Injection context", type="choice", choices=CONTEXTS,
                   default="unknown", prompt="Injection context"),
            Option("mode", "Detection method", type="choice", choices=MODES,
                   default="detection", prompt="Mode"),
        ]

    def build(self, ctx: dict[str, Any], library) -> BuildOutput:
        ctx = self.apply_defaults(ctx)
        dbms = str(ctx.get("dbms", "generic")).lower()
        context = str(ctx.get("context", "unknown")).lower()
        mode = str(ctx.get("mode", "detection")).lower()
        if dbms not in DBMS:
            raise ModuleError(f"dbms must be one of: {', '.join(DBMS)}")
        if context not in CONTEXTS:
            raise ModuleError(f"context must be one of: {', '.join(CONTEXTS)}")
        if mode not in MODES:
            raise ModuleError(f"mode must be one of: {', '.join(MODES)}")

        templates = library.by_category("sqli")

        # DBMS filter: selected engine OR generic (generic always applies).
        engine_filter = {dbms, "generic"} if dbms != "generic" else {"generic"}
        # Context filter: unknown => all contexts.
        context_filter = None if context == "unknown" else {context}
        # Mode filter: detection => include detection + boolean + error (broad).
        if mode == "detection":
            mode_filter = {"detection", "boolean", "error"}
        else:
            mode_filter = {mode}

        selected = select_templates(
            templates, engine=engine_filter, context=context_filter, mode=mode_filter
        )

        units = [
            Unit(
                value=t.template,  # no placeholders in SQLi builtins
                transforms=(),     # raw: Burp applies URL encoding to params
                family=f"{t.engine}:{t.context}:{t.mode}",
                template_id=t.id,
                note=t.notes,
            )
            for t in selected
        ]
        if not units:
            raise ModuleError(
                f"No SQLi templates for dbms={dbms}, context={context}, mode={mode}."
            )

        notes = [
            "SQLi payloads are raw. Burp Intruder will URL-encode them for the "
            "request; keep 'URL-encode these characters' at its default unless the "
            "insertion point is already encoded.",
            "Boolean pairs (true/false) must be compared against each other; a "
            "payload reflected in a response is not proof of injection.",
        ]
        info = {
            "Category": "SQL Injection",
            "DBMS": dbms,
            "Context": context,
            "Mode": mode,
        }
        return BuildOutput(units=units, info=info, notes=notes)


register(SQLiModule())
