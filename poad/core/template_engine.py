"""Data-driven payload template engine.

Templates are *data*, never executable code. A template is a string containing
``<<POAD_NAME>>`` placeholder tokens plus metadata describing when it applies and
which transformations are safe. Substitution is a literal string replacement --
there is no ``eval``, no format-string interpretation, and no shell execution --
so literal payload characters (braces ``{{}}``, slashes, quotes) are preserved
exactly.

Placeholder syntax: ``<<POAD_FILE>>``, ``<<POAD_COMMAND>>`` etc. We deliberately
avoid ``{NAME}`` style because security payloads frequently contain literal
braces (SSTI).
"""

from __future__ import annotations

import importlib.resources as resources
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

_TOKEN_RE = re.compile(r"<<POAD_([A-Z0-9_]+)>>")

# Fields permitted in a template definition. Unknown keys are rejected on
# validation so typos surface instead of being silently ignored.
_ALLOWED_TEMPLATE_KEYS = {
    "id",
    "name",
    "category",
    "template",
    "required",
    "platform",
    "engine",
    "mode",
    "context",
    "tags",
    "transforms",
    "expected",
    "notes",
    "source",
    "version_dependent",
    "multiline",
    "whole_document",
}

_ALLOWED_PACK_KEYS = {
    "pack",
    "category",
    "source",
    "license",
    "attribution",
    "templates",
}


class TemplateError(ValueError):
    """Raised when a template or template pack is invalid."""


@dataclass(frozen=True)
class Template:
    id: str
    name: str
    category: str
    template: str
    required: tuple[str, ...] = ()
    platform: str | None = None
    engine: str | None = None
    mode: str | None = None
    context: str | None = None
    tags: tuple[str, ...] = ()
    transforms: tuple[str, ...] = ()
    expected: str | None = None
    notes: str | None = None
    source: str = "builtin"
    version_dependent: bool = False
    multiline: bool = False
    whole_document: bool = False

    def tokens(self) -> set[str]:
        """Return the set of placeholder token names present in the template."""
        return set(_TOKEN_RE.findall(self.template))


def find_tokens(template: str) -> set[str]:
    return set(_TOKEN_RE.findall(template))


def substitute(template: str, values: dict[str, str]) -> str:
    """Replace every ``<<POAD_NAME>>`` with ``values['NAME']`` (literal replace).

    Raises :class:`TemplateError` if a token present in the template has no value.
    """
    missing: list[str] = []

    def _repl(match: "re.Match[str]") -> str:
        name = match.group(1)
        if name not in values:
            missing.append(name)
            return match.group(0)
        return values[name]

    result = _TOKEN_RE.sub(_repl, template)
    if missing:
        raise TemplateError(
            "Missing template variable(s): " + ", ".join(sorted(set(missing)))
        )
    return result


def _coerce_str_tuple(value: Any, field_name: str, template_id: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise TemplateError(
            f"Template {template_id!r}: field {field_name!r} must be a list of strings"
        )
    return tuple(value)


def template_from_dict(data: dict[str, Any], *, default_source: str = "builtin") -> Template:
    if not isinstance(data, dict):
        raise TemplateError("Template entry must be an object")

    unknown = set(data) - _ALLOWED_TEMPLATE_KEYS
    if unknown:
        raise TemplateError(
            "Unknown template field(s): " + ", ".join(sorted(unknown))
        )

    for req in ("id", "name", "category", "template"):
        if req not in data or not isinstance(data[req], str) or not data[req]:
            raise TemplateError(f"Template missing required string field {req!r}")

    tpl_id = data["id"]
    tpl = Template(
        id=tpl_id,
        name=data["name"],
        category=data["category"],
        template=data["template"],
        required=_coerce_str_tuple(data.get("required"), "required", tpl_id),
        platform=data.get("platform"),
        engine=data.get("engine"),
        mode=data.get("mode"),
        context=data.get("context"),
        tags=_coerce_str_tuple(data.get("tags"), "tags", tpl_id),
        transforms=_coerce_str_tuple(data.get("transforms"), "transforms", tpl_id),
        expected=data.get("expected"),
        notes=data.get("notes"),
        source=data.get("source", default_source),
        version_dependent=bool(data.get("version_dependent", False)),
        multiline=bool(data.get("multiline", False)),
        whole_document=bool(data.get("whole_document", False)),
    )

    # Cross-check: every token in the template string must be declared required,
    # and every declared required var must appear as a token.
    tokens = tpl.tokens()
    required_tokens = {r.upper() for r in tpl.required}
    undeclared = tokens - required_tokens
    if undeclared:
        raise TemplateError(
            f"Template {tpl_id!r}: placeholder(s) {sorted(undeclared)} "
            "not listed in 'required'"
        )
    unused = required_tokens - tokens
    if unused:
        raise TemplateError(
            f"Template {tpl_id!r}: 'required' var(s) {sorted(unused)} "
            "never used in template string"
        )

    # Validate transform names against the registry (import locally to avoid cycle).
    from poad.core import transformations

    for tname in tpl.transforms:
        if tname not in transformations.REGISTRY:
            raise TemplateError(
                f"Template {tpl_id!r}: unknown transform {tname!r}"
            )
    return tpl


@dataclass
class TemplatePack:
    name: str
    category: str
    source: str
    templates: list[Template] = field(default_factory=list)
    license: str | None = None
    attribution: str | None = None


def pack_from_dict(data: dict[str, Any]) -> TemplatePack:
    if not isinstance(data, dict):
        raise TemplateError("Template pack must be a JSON object")
    unknown = set(data) - _ALLOWED_PACK_KEYS
    if unknown:
        raise TemplateError("Unknown pack field(s): " + ", ".join(sorted(unknown)))
    if "templates" not in data or not isinstance(data["templates"], list):
        raise TemplateError("Template pack must contain a 'templates' list")

    source = data.get("source", "builtin")
    templates = [
        template_from_dict(entry, default_source=source) for entry in data["templates"]
    ]
    seen: set[str] = set()
    for tpl in templates:
        if tpl.id in seen:
            raise TemplateError(f"Duplicate template id in pack: {tpl.id!r}")
        seen.add(tpl.id)

    return TemplatePack(
        name=data.get("pack", "unnamed"),
        category=data.get("category", templates[0].category if templates else "unknown"),
        source=source,
        templates=templates,
        license=data.get("license"),
        attribution=data.get("attribution"),
    )


def template_to_dict(tpl: Template) -> dict[str, Any]:
    """Serialise a Template to a plain dict (omitting empty/default fields)."""
    data: dict[str, Any] = {
        "id": tpl.id,
        "name": tpl.name,
        "category": tpl.category,
        "template": tpl.template,
    }
    if tpl.required:
        data["required"] = list(tpl.required)
    for attr in ("platform", "engine", "mode", "context", "expected", "notes"):
        value = getattr(tpl, attr)
        if value is not None:
            data[attr] = value
    if tpl.tags:
        data["tags"] = list(tpl.tags)
    if tpl.transforms:
        data["transforms"] = list(tpl.transforms)
    if tpl.source and tpl.source != "builtin":
        data["source"] = tpl.source
    if tpl.version_dependent:
        data["version_dependent"] = True
    if tpl.multiline:
        data["multiline"] = True
    if tpl.whole_document:
        data["whole_document"] = True
    return data


def pack_to_dict(pack: TemplatePack) -> dict[str, Any]:
    data: dict[str, Any] = {
        "pack": pack.name,
        "category": pack.category,
        "source": pack.source,
        "templates": [template_to_dict(t) for t in pack.templates],
    }
    if pack.license:
        data["license"] = pack.license
    if pack.attribution:
        data["attribution"] = pack.attribution
    return data


def load_pack_file(path: str | Path) -> TemplatePack:
    """Load and validate a template pack from a JSON file on disk."""
    p = Path(path)
    try:
        raw = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise TemplateError(f"Cannot read template pack {p}: {exc}") from exc
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise TemplateError(f"Invalid JSON in {p}: {exc}") from exc
    return pack_from_dict(data)


class TemplateLibrary:
    """In-memory index of all loaded templates, keyed by id and by category."""

    def __init__(self) -> None:
        self._by_id: dict[str, Template] = {}
        self._by_category: dict[str, list[Template]] = {}

    def add_pack(self, pack: TemplatePack) -> None:
        for tpl in pack.templates:
            self.add(tpl)

    def add(self, tpl: Template) -> None:
        # Later packs override earlier ids (allows user packs to shadow builtins).
        if tpl.id in self._by_id:
            old = self._by_id[tpl.id]
            self._by_category.get(old.category, []).remove(old)
        self._by_id[tpl.id] = tpl
        self._by_category.setdefault(tpl.category, []).append(tpl)

    def get(self, template_id: str) -> Template | None:
        return self._by_id.get(template_id)

    def by_category(self, category: str) -> list[Template]:
        return list(self._by_category.get(category, []))

    def all(self) -> list[Template]:
        return list(self._by_id.values())

    def categories(self) -> list[str]:
        return sorted(self._by_category.keys())

    def __len__(self) -> int:
        return len(self._by_id)


def _builtin_templates_root():
    return resources.files("poad").joinpath("templates")


def load_builtin_library() -> TemplateLibrary:
    """Load every builtin template pack shipped inside the package."""
    lib = TemplateLibrary()
    root = _builtin_templates_root()
    for pack_path in _iter_json_resources(root):
        text = pack_path.read_text(encoding="utf-8")
        try:
            data = json.loads(text)
        except ValueError as exc:  # pragma: no cover - would indicate a packaging bug
            raise TemplateError(f"Corrupt builtin pack {pack_path!r}: {exc}") from exc
        lib.add_pack(pack_from_dict(data))
    return lib


def load_user_packs(lib: TemplateLibrary, directory: Path) -> list[str]:
    """Load user template packs from a directory. Returns a list of warnings.

    Malformed user packs are skipped with a warning rather than crashing startup.
    """
    warnings: list[str] = []
    if not directory.exists():
        return warnings
    for pack_path in sorted(directory.rglob("*.json")):
        try:
            lib.add_pack(load_pack_file(pack_path))
        except TemplateError as exc:
            warnings.append(f"Skipped invalid user pack {pack_path.name}: {exc}")
    return warnings


def load_library(user_dir: Path | None = None) -> tuple[TemplateLibrary, list[str]]:
    """Load builtin templates plus any user packs. Returns (library, warnings)."""
    lib = load_builtin_library()
    warnings: list[str] = []
    if user_dir is not None:
        warnings = load_user_packs(lib, user_dir)
    return lib, warnings


def _iter_json_resources(root) -> Iterable:
    """Yield all ``*.json`` Traversable resources under ``root`` (recursively)."""
    if not root.is_dir():
        return
    for entry in sorted(root.iterdir(), key=lambda e: e.name):
        if entry.is_dir():
            yield from _iter_json_resources(entry)
        elif entry.name.endswith(".json"):
            yield entry
