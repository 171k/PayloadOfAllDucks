"""Template engine / library tests."""

from __future__ import annotations

import json

import pytest

from poad.core import template_engine as te


def test_builtin_library_loads(library):
    assert len(library) > 0
    for cat in ("lfi", "ssti", "sqli", "xss", "command_injection", "ssrf", "xxe"):
        # lfi/ssrf are generated programmatically; they may have 0 builtin templates.
        assert isinstance(library.by_category(cat), list)
    assert library.by_category("ssti")  # SSTI is template-driven


def test_substitute_literal_only():
    out = te.substitute("read <<POAD_FILE>> now", {"FILE": "/etc/passwd"})
    assert out == "read /etc/passwd now"


def test_substitute_preserves_braces():
    # A literal brace next to a placeholder must survive.
    out = te.substitute("{{x}}<<POAD_MARKER>>", {"MARKER": "M"})
    assert out == "{{x}}M"


def test_substitute_missing_var_raises():
    with pytest.raises(te.TemplateError):
        te.substitute("<<POAD_FILE>>", {})


def test_template_requires_declared_tokens():
    with pytest.raises(te.TemplateError):
        te.template_from_dict({
            "id": "t", "name": "t", "category": "x",
            "template": "<<POAD_FILE>>",  # token not declared in required
        })


def test_template_unused_required_raises():
    with pytest.raises(te.TemplateError):
        te.template_from_dict({
            "id": "t", "name": "t", "category": "x",
            "template": "no tokens", "required": ["file"],
        })


def test_template_unknown_field_rejected():
    with pytest.raises(te.TemplateError):
        te.template_from_dict({
            "id": "t", "name": "t", "category": "x",
            "template": "x", "danger": "rm -rf /",
        })


def test_template_unknown_transform_rejected():
    with pytest.raises(te.TemplateError):
        te.template_from_dict({
            "id": "t", "name": "t", "category": "x",
            "template": "x", "transforms": ["evil_transform"],
        })


def test_pack_roundtrip():
    tpl = te.Template(id="a", name="A", category="lfi", template="x")
    pack = te.TemplatePack(name="p", category="lfi", source="builtin", templates=[tpl])
    data = te.pack_to_dict(pack)
    restored = te.pack_from_dict(data)
    assert restored.templates[0].id == "a"


def test_load_pack_file(tmp_path):
    data = {
        "pack": "custom", "category": "lfi", "source": "custom",
        "templates": [{"id": "c1", "name": "c1", "category": "lfi", "template": "/x"}],
    }
    f = tmp_path / "pack.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    pack = te.load_pack_file(f)
    assert pack.templates[0].id == "c1"


def test_load_pack_file_bad_json(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{not json", encoding="utf-8")
    with pytest.raises(te.TemplateError):
        te.load_pack_file(f)


def test_duplicate_id_in_pack_rejected():
    with pytest.raises(te.TemplateError):
        te.pack_from_dict({
            "pack": "p", "category": "lfi", "templates": [
                {"id": "dup", "name": "a", "category": "lfi", "template": "x"},
                {"id": "dup", "name": "b", "category": "lfi", "template": "y"},
            ],
        })
