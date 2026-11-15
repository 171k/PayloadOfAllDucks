"""Cross-platform configuration and storage paths for POAD.

Presets and user settings are stored in a per-user config directory following
platform conventions. Everything is plain JSON (human readable). No secrets or
target credentials are ever written here by POAD itself.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

APP_DIRNAME = "poad"


def _config_root() -> Path:
    """Return the base configuration directory for the current platform."""
    override = os.environ.get("POAD_CONFIG_DIR")
    if override:
        return Path(override).expanduser()

    if os.name == "nt":  # Windows
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_DIRNAME
        return Path.home() / "AppData" / "Roaming" / APP_DIRNAME

    # POSIX (Linux first-class, macOS acceptable)
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / APP_DIRNAME
    return Path.home() / ".config" / APP_DIRNAME


def config_dir() -> Path:
    return _config_root()


def presets_dir() -> Path:
    return _config_root() / "presets"


def settings_path() -> Path:
    return _config_root() / "settings.json"


def user_templates_dir() -> Path:
    """Directory for imported/custom template packs (loaded at startup)."""
    return _config_root() / "templates"


def ensure_dirs() -> None:
    """Create config/preset/template directories if they do not already exist."""
    presets_dir().mkdir(parents=True, exist_ok=True)
    user_templates_dir().mkdir(parents=True, exist_ok=True)


DEFAULT_SETTINGS: dict[str, Any] = {
    "schema_version": 1,
    # Burp payload handling guidance mode: "raw" | "pre-encoded" | "mixed"
    "burp_mode": "raw",
    # Default export format for interactive mode.
    "default_format": "txt",
    # Hard cap on generated payloads to avoid combinatorial explosions.
    "max_payloads": 50000,
    # Warn before generating more than this many payloads.
    "large_warn_threshold": 2000,
    # Use rich terminal output when available.
    "use_rich": True,
    # Use the unicode duck banner when the terminal supports it.
    "unicode_banner": True,
}


def load_settings() -> dict[str, Any]:
    """Load settings, merging over defaults. Corrupt files fall back to defaults."""
    path = settings_path()
    settings = dict(DEFAULT_SETTINGS)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                settings.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
        except (OSError, ValueError):
            # Corrupted settings: ignore and use defaults rather than crashing.
            pass
    return settings


def save_settings(settings: dict[str, Any]) -> None:
    ensure_dirs()
    path = settings_path()
    merged = dict(DEFAULT_SETTINGS)
    merged.update({k: v for k, v in settings.items() if k in DEFAULT_SETTINGS})
    path.write_text(json.dumps(merged, indent=2, sort_keys=True) + "\n", encoding="utf-8")
