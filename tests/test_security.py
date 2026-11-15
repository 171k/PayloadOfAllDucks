"""Security-focused tests.

These assert the properties the project spec calls out: no code execution from
inputs or templates, no network, bounded generation, and safe path handling.
"""

from __future__ import annotations

import socket

import pytest

from poad.core import generator, template_engine
from poad.core.generator import Unit
from poad.modules import get_module
from poad.presets import PresetError, validate_name


def test_templates_are_data_not_code():
    # Substitution is literal; a payload containing python is never evaluated.
    out = template_engine.substitute(
        "<<POAD_FILE>>", {"FILE": "__import__('os').system('id')"}
    )
    assert out == "__import__('os').system('id')"


def test_no_eval_in_template_values():
    tpl = template_engine.Template(
        id="x", name="x", category="x", template="{{<<POAD_MARKER>>}}", required=("marker",)
    )
    rendered = template_engine.substitute(tpl.template, {"MARKER": "7*7"})
    # The arithmetic is NOT evaluated by POAD; braces preserved literally.
    assert rendered == "{{7*7}}"


def test_command_injection_default_library_is_harmless(library):
    module = get_module("cmdi")
    build = module.build({"os": "linux"}, library)
    joined = "\n".join(u.value for u in build.units)
    for bad in ("nc ", "bash -i", "/dev/tcp", "rm -rf", "curl ", "wget ", "powershell -enc"):
        assert bad not in joined


def test_no_network_access(monkeypatch, library):
    # Guard: generation must not open any socket.
    def boom(*a, **k):
        raise AssertionError("network access attempted during generation")

    monkeypatch.setattr(socket.socket, "connect", boom)
    for key, ctx in {
        "lfi": {"file": "/a/b"},
        "ssti": {"engine": "jinja2", "mode": "detection"},
        "sqli": {"dbms": "mysql"},
        "xss": {"context": "html"},
        "cmdi": {"os": "linux"},
        "ssrf": {"host": "127.0.0.1"},
        "xxe": {"mode": "detection"},
    }.items():
        module = get_module(key)
        build = module.build(ctx, library)
        generator.generate(build.units, encodings="all")


def test_bounded_generation():
    units = [Unit(value=f"p{i}", transforms=()) for i in range(1000)]
    result = generator.generate(units, encodings="raw", max_payloads=50)
    assert result.stats["final_payloads"] == 50


def test_preset_name_rejects_path_traversal():
    with pytest.raises(PresetError):
        validate_name("../../etc/passwd")
    with pytest.raises(PresetError):
        validate_name("a/b")
    assert validate_name("flag-lfi") == "flag-lfi"


def test_resource_within(tmp_path):
    from poad.core.validation import resource_within
    base = tmp_path / "base"
    base.mkdir()
    inside = base / "x.txt"
    inside.write_text("x", encoding="utf-8")
    assert resource_within(base, inside)
    assert not resource_within(base, tmp_path / "outside.txt")
