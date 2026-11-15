"""SSTI module tests."""

from __future__ import annotations

import pytest

from poad.core import generator
from poad.modules import get_module
from poad.modules.base import ModuleError


def gen(ctx, library):
    module = get_module("ssti")
    build = module.build(ctx, library)
    result = generator.generate(build.units, encodings="all")
    return result.payloads


def test_jinja2_detection(library):
    payloads = gen({"engine": "jinja2", "mode": "detection"}, library)
    assert "{{7*7}}" in payloads
    assert "{{7*'7'}}" in payloads


def test_brace_preservation_no_encoding(library):
    # Even with encoding=all requested, SSTI units declare no transforms, so
    # braces and quotes must be emitted raw.
    module = get_module("ssti")
    build = module.build({"engine": "jinja2", "mode": "detection"}, library)
    result = generator.generate(build.units, encodings="all")
    assert "{{7*7}}" in result.payloads
    assert all("%7B" not in p and "&#" not in p for p in result.payloads)


def test_no_cross_engine_mixing(library):
    payloads = gen({"engine": "jinja2", "mode": "detection"}, library)
    # No ERB/Freemarker/Smarty syntax should appear.
    joined = "\n".join(payloads)
    assert "<%" not in joined
    assert "${" not in joined
    assert "{$smarty" not in joined


def test_file_read_substitution(library):
    payloads = gen(
        {"engine": "mako", "mode": "file-read", "file": "/flag/flag.txt"}, library
    )
    assert any("/flag/flag.txt" in p for p in payloads)
    assert any("<<POAD_" not in p for p in payloads)
    assert all("<<POAD_" not in p for p in payloads)


def test_file_read_requires_file(library):
    module = get_module("ssti")
    with pytest.raises(ModuleError):
        module.build({"engine": "mako", "mode": "file-read"}, library)


def test_unknown_engine_rejected(library):
    module = get_module("ssti")
    with pytest.raises(ModuleError):
        module.build({"engine": "nope", "mode": "detection"}, library)


def test_django_file_read_unsupported(library):
    # Django has no file-read template -> honest limitation, not fabricated output.
    module = get_module("ssti")
    with pytest.raises(ModuleError):
        module.build({"engine": "django", "mode": "file-read"}, library)


def test_marker_substitution(library):
    payloads = gen({"engine": "twig", "mode": "identification", "marker": "DUCK"}, library)
    assert any("DUCK" in p for p in payloads)


def test_deterministic(library):
    a = gen({"engine": "jinja2", "mode": "detection"}, library)
    b = gen({"engine": "jinja2", "mode": "detection"}, library)
    assert a == b
