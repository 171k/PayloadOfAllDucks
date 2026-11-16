"""Module base class, option model, and registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from poad.core.generator import Unit


@dataclass
class Option:
    """Describes one user input for a module (drives CLI + interactive prompts)."""

    name: str
    help: str
    type: str = "str"  # str | int | choice | multichoice | flag
    required: bool = False
    default: Any = None
    choices: tuple[str, ...] = ()
    prompt: str = ""
    # Short example value shown in interactive prompts / CLI help.
    example: str = ""
    # Only ask this option interactively when ctx[gate_field] == gate_value.
    gate_field: str | None = None
    gate_value: Any = None

    def applies(self, ctx: dict[str, Any]) -> bool:
        if self.gate_field is None:
            return True
        return ctx.get(self.gate_field) == self.gate_value


@dataclass
class BuildOutput:
    units: list[Unit] = field(default_factory=list)
    info: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class ModuleError(ValueError):
    """Raised when a module cannot build payloads from the given context."""


# Friendly ``--encoding`` aliases -> a set of transform names (or sentinels).
ENCODING_ALIASES: dict[str, Any] = {
    "all": "all",
    "raw": "raw",
    "none": "raw",
    "url": {"url_sep", "url_sep_upper", "url_all"},
    "double": {"double_url_sep", "url_all_double"},
    "html": {"html_entity", "html_entity_hex", "html_entity_decimal"},
}


def resolve_encoding(value: str | None):
    """Translate a user ``--encoding`` value into a generator ``encodings`` arg."""
    if value is None:
        return "all"
    v = value.strip().lower()
    if v in ENCODING_ALIASES:
        return ENCODING_ALIASES[v]
    # Otherwise treat as a comma-separated list of explicit transform names.
    names = {part.strip() for part in v.split(",") if part.strip()}
    return names or "all"


class BaseModule:
    key: str = ""
    aliases: tuple[str, ...] = ()
    title: str = ""
    summary: str = ""

    def options(self) -> list[Option]:
        raise NotImplementedError

    def build(self, ctx: dict[str, Any], library) -> BuildOutput:
        raise NotImplementedError

    # -- shared helpers -------------------------------------------------

    def option(self, name: str) -> Option | None:
        for opt in self.options():
            if opt.name == name:
                return opt
        return None

    def apply_defaults(self, ctx: dict[str, Any]) -> dict[str, Any]:
        merged = dict(ctx)
        for opt in self.options():
            if merged.get(opt.name) in (None, "") and opt.default is not None:
                merged[opt.name] = opt.default
        return merged

    def require(self, ctx: dict[str, Any], *names: str) -> None:
        missing = [n for n in names if ctx.get(n) in (None, "")]
        if missing:
            raise ModuleError(
                "Missing required option(s): " + ", ".join(missing)
            )


def field_matches(value: Any, accepted) -> bool:
    """True if a template field ``value`` matches an ``accepted`` selection.

    A template value of ``None`` or ``"any"`` matches any selection (the template
    is context-agnostic). ``accepted`` of ``None`` means "no filter".
    """
    if accepted is None:
        return True
    if value in (None, "any"):
        return True
    if isinstance(accepted, str):
        return value == accepted
    return value in accepted


def select_templates(templates, **filters):
    """Filter templates by attribute. Each filter value may be a str or a set."""
    out = []
    for tpl in templates:
        if all(field_matches(getattr(tpl, attr, None), acc) for attr, acc in filters.items()):
            out.append(tpl)
    return out


_REGISTRY: dict[str, BaseModule] = {}


def register(module: BaseModule) -> BaseModule:
    _REGISTRY[module.key] = module
    for alias in module.aliases:
        _REGISTRY[alias] = module
    return module


def get_module(name: str) -> BaseModule | None:
    return _REGISTRY.get(name.lower().strip())


def iter_modules() -> Iterable[BaseModule]:
    """Yield each distinct module once, in canonical registration order."""
    seen: set[int] = set()
    for mod in _REGISTRY.values():
        if id(mod) in seen:
            continue
        seen.add(id(mod))
        yield mod
