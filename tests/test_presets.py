"""Preset save/load/run tests."""

from __future__ import annotations

import pytest

from poad import cli, presets


def test_save_and_load_roundtrip():
    p = presets.Preset(name="flag-lfi", category="lfi",
                       options={"file": "/flag/flag.txt", "depth": 8}, encoding="all")
    presets.save_preset(p)
    loaded = presets.load_preset("flag-lfi")
    assert loaded.category == "lfi"
    assert loaded.options["file"] == "/flag/flag.txt"
    assert "flag-lfi" in presets.list_presets()


def test_corrupted_preset(tmp_path, monkeypatch):
    path = presets.preset_path("broken")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(presets.PresetError):
        presets.load_preset("broken")


def test_missing_preset():
    with pytest.raises(presets.PresetError):
        presets.load_preset("does-not-exist")


def test_delete_preset():
    presets.save_preset(presets.Preset(name="tmp", category="lfi", options={"file": "/a"}))
    assert presets.delete_preset("tmp") is True
    assert presets.delete_preset("tmp") is False


def test_save_preset_via_cli_and_run(tmp_path):
    out = tmp_path / "pl.txt"
    rc = cli.main([
        "generate", "lfi", "--file", "/flag/flag.txt", "--os", "linux",
        "--depth", "4", "--output", str(out), "--force", "-q",
        "--save-preset", "flag-lfi",
    ])
    assert rc == 0
    assert "flag-lfi" in presets.list_presets()

    out2 = tmp_path / "pl2.txt"
    rc2 = cli.main(["presets", "run", "flag-lfi", "-o", str(out2), "--force"])
    assert rc2 == 0
    assert out2.read_text(encoding="utf-8") == out.read_text(encoding="utf-8")


def test_preset_run_output_matches_direct(tmp_path):
    # A preset reproduces the same deterministic output.
    direct = tmp_path / "direct.txt"
    cli.main(["generate", "sqli", "--dbms", "mysql", "--context", "string",
              "--output", str(direct), "--force", "-q", "--save-preset", "mysqlstr"])
    via = tmp_path / "via.txt"
    cli.main(["presets", "run", "mysqlstr", "-o", str(via), "--force"])
    assert direct.read_text(encoding="utf-8") == via.read_text(encoding="utf-8")
