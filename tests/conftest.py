"""Shared pytest fixtures: isolate POAD config/presets to a temp dir."""

from __future__ import annotations

import pytest

from poad.core import template_engine


@pytest.fixture(autouse=True)
def isolate_config(tmp_path, monkeypatch):
    monkeypatch.setenv("POAD_CONFIG_DIR", str(tmp_path / "poadcfg"))
    yield


@pytest.fixture
def library():
    return template_engine.load_builtin_library()
