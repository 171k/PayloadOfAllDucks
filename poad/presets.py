"""Saved generation presets (configuration only -- never generated payloads).

Presets are small JSON files under the user config directory. They store the
category and the option values needed to reproduce a generation. They never
contain payloads, secrets, or target credentials.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from poad import __version__, config

PRESET_SCHEMA_VERSION = 1
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class PresetError(ValueError):
    pass


@dataclass
class Preset:
    name: str
    category: str
    options: dict[str, Any] = field(default_factory=dict)
    encoding: str = "all"
    fmt: str = "txt"
    max_payloads: int | None = None
    schema_version: int = PRESET_SCHEMA_VERSION
    created_with: str = __version__

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "category": self.category,
            "options": self.options,
            "encoding": self.encoding,
            "format": self.fmt,
            "max_payloads": self.max_payloads,
            "created_with": self.created_with,
        }


def validate_name(name: str) -> str:
    if not _NAME_RE.match(name or ""):
        raise PresetError(
            "Invalid preset name. Use letters, digits, '.', '_', '-' "
            "(max 64 chars, no path separators)."
        )
    return name


def preset_path(name: str) -> Path:
    validate_name(name)
    return config.presets_dir() / f"{name}.json"


def save_preset(preset: Preset) -> Path:
    validate_name(preset.name)
    config.ensure_dirs()
    path = preset_path(preset.name)
    path.write_text(json.dumps(preset.to_dict(), indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return path


def load_preset(name: str) -> Preset:
    path = preset_path(name)
    if not path.exists():
        raise PresetError(f"Preset not found: {name}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PresetError(f"Corrupted preset {name}: {exc}") from exc
    if not isinstance(data, dict):
        raise PresetError(f"Corrupted preset {name}: not an object")
    try:
        return Preset(
            name=data.get("name", name),
            category=data["category"],
            options=dict(data.get("options", {})),
            encoding=data.get("encoding", "all"),
            fmt=data.get("format", "txt"),
            max_payloads=data.get("max_payloads"),
            schema_version=int(data.get("schema_version", PRESET_SCHEMA_VERSION)),
            created_with=data.get("created_with", "unknown"),
        )
    except KeyError as exc:
        raise PresetError(f"Preset {name} missing field: {exc}") from exc


def list_presets() -> list[str]:
    d = config.presets_dir()
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.json"))


def delete_preset(name: str) -> bool:
    path = preset_path(name)
    if path.exists():
        path.unlink()
        return True
    return False
