"""Custom template pack loading and extensibility."""

from __future__ import annotations

import shutil
from pathlib import Path

from poad import config
from poad.core import template_engine

FIXTURES = Path(__file__).parent / "fixtures"


def test_custom_pack_validates():
    pack = template_engine.load_pack_file(FIXTURES / "custom_lfi_pack.json")
    assert pack.category == "lfi"
    assert len(pack.templates) == 2


def test_user_pack_loaded_into_library(tmp_path, monkeypatch):
    # Drop a custom pack into the user templates dir and confirm it loads,
    # proving templates can be extended without touching Python source.
    user_dir = config.user_templates_dir()
    (user_dir / "lfi").mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / "custom_lfi_pack.json", user_dir / "lfi" / "demo.json")

    lib, warnings = template_engine.load_library(user_dir)
    assert warnings == []
    assert lib.get("custom-lfi-proc-self-environ") is not None


def test_invalid_user_pack_is_skipped_with_warning(tmp_path):
    user_dir = config.user_templates_dir()
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / "broken.json").write_text("{not json", encoding="utf-8")
    lib, warnings = template_engine.load_library(user_dir)
    # Builtins still load; the broken pack is reported, not fatal.
    assert len(lib) > 0
    assert any("broken.json" in w for w in warnings)
