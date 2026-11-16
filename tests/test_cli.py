"""CLI integration tests (call poad.cli.main directly)."""

from __future__ import annotations

import subprocess
import sys

import pytest

from poad import cli


def test_version(capsys):
    from poad import __version__
    assert cli.main(["version"]) == 0
    out = capsys.readouterr().out
    assert __version__ in out


def test_list(capsys):
    assert cli.main(["list"]) == 0
    out = capsys.readouterr().out
    assert "lfi" in out and "ssti" in out


def test_list_category(capsys):
    assert cli.main(["list", "ssti"]) == 0
    out = capsys.readouterr().out
    assert "jinja2" in out


def test_generate_lfi(tmp_path, capsys):
    out = tmp_path / "pl.txt"
    rc = cli.main([
        "generate", "lfi", "--file", "/flag/flag.txt", "--os", "linux",
        "--depth", "8", "--output", str(out), "-q",
    ])
    assert rc == 0
    lines = out.read_text(encoding="utf-8").splitlines()
    assert "/flag/flag.txt" in lines
    assert "../../flag/flag.txt" in lines
    assert "..%2fflag%2fflag.txt" in lines


def test_generate_ssti(tmp_path):
    out = tmp_path / "ssti.txt"
    rc = cli.main([
        "generate", "ssti", "--engine", "jinja2", "--mode", "detection",
        "--output", str(out), "-q",
    ])
    assert rc == 0
    body = out.read_text(encoding="utf-8")
    assert "{{7*7}}" in body


def test_missing_required_option(capsys):
    # lfi requires --file; argparse should error with non-zero exit.
    rc = cli.main(["generate", "lfi", "-o", "x.txt"])
    assert rc != 0


def test_bad_category(capsys):
    rc = cli.main(["generate", "nope"])
    assert rc == 2
    err = capsys.readouterr()
    assert "Unknown category" in (err.out + err.err)


def test_help_exits_zero():
    rc = cli.main(["generate", "lfi", "--help"])
    assert rc == 0


def test_overwrite_protection(tmp_path, capsys):
    out = tmp_path / "pl.txt"
    out.write_text("existing", encoding="utf-8")
    rc = cli.main([
        "generate", "lfi", "--file", "/a/b", "--output", str(out), "-q",
    ])
    assert rc == 1  # refuses to overwrite
    rc2 = cli.main([
        "generate", "lfi", "--file", "/a/b", "--output", str(out), "--force", "-q",
    ])
    assert rc2 == 0


def test_preview_no_file(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["preview", "lfi", "--file", "/a/b", "--depth", "2"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "../a/b" in out
    assert not (tmp_path / "payloadlist.txt").exists()


def test_doctor():
    assert cli.main(["doctor"]) == 0


def test_python_dash_m_entrypoint():
    result = subprocess.run(
        [sys.executable, "-m", "poad", "version"],
        capture_output=True, text=True,
    )
    from poad import __version__
    assert result.returncode == 0
    assert __version__ in result.stdout


def test_templates_list(capsys):
    assert cli.main(["templates", "list"]) == 0
    out = capsys.readouterr().out
    assert "ssti-jinja2-detect-mul" in out
