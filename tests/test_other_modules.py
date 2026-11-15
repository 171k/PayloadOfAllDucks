"""Tests for SQLi, XSS, Command Injection, SSRF, XXE modules."""

from __future__ import annotations

import pytest

from poad.core import generator
from poad.core.validation import is_valid_line
from poad.modules import get_module
from poad.modules.base import ModuleError


def payloads(key, ctx, library, encoding="all"):
    build = get_module(key).build(ctx, library)
    return generator.generate(build.units, encodings=encoding).payloads


def test_sqli_no_dialect_mixing(library):
    # MySQL selection must not include Postgres/MSSQL-only payloads.
    out = payloads("sqli", {"dbms": "mysql", "context": "string", "mode": "error"}, library)
    joined = "\n".join(out)
    assert "convert(int,@@version)" not in joined  # MSSQL
    assert "cast(version() as int)" not in joined   # Postgres
    assert any("extractvalue" in p for p in out)    # MySQL present


def test_sqli_context_numeric(library):
    out = payloads("sqli", {"dbms": "generic", "context": "numeric", "mode": "boolean"}, library)
    assert "1 OR 1=1" in out
    assert "' OR '1'='1" not in out  # string-context payload excluded


def test_xss_context_filtering(library):
    out = payloads("xss", {"context": "js-string"}, library)
    assert any("alert('POAD')" in p for p in out)
    assert all("<script>" not in p for p in out)  # html-body excluded


def test_cmdi_separators_and_default_command(library):
    out = payloads("cmdi", {"os": "linux"}, library)
    assert "; id" in out
    assert "| id" in out
    assert "$(id)" in out


def test_cmdi_windows_default(library):
    out = payloads("cmdi", {"os": "windows"}, library)
    assert "& whoami" in out


def test_ssrf_requires_host(library):
    with pytest.raises(ModuleError):
        get_module("ssrf").build({}, library)


def test_ssrf_ip_variants(library):
    out = payloads("ssrf", {"host": "127.0.0.1", "scheme": "http", "path": "/"}, library)
    assert "http://127.0.0.1/" in out
    # Alternate IPv4 encodings present (decimal int for 127.0.0.1 == 2130706433).
    assert any("2130706433" in p for p in out)


def test_ssrf_no_default_targets(library):
    # With only a host given, nothing references metadata/other hosts.
    out = payloads("ssrf", {"host": "example.test"}, library)
    joined = "\n".join(out)
    assert "169.254.169.254" not in joined
    assert "metadata" not in joined


def test_xxe_whole_document_single_line(library):
    out = payloads("xxe", {"mode": "file-read", "file": "/etc/passwd"}, library)
    assert out, "expected XXE payloads"
    for p in out:
        assert is_valid_line(p)  # single line, no embedded newline
        assert p.startswith("<?xml")
    assert any("/etc/passwd" in p for p in out)


def test_xxe_detection_marker(library):
    out = payloads("xxe", {"mode": "detection", "marker": "DUCK"}, library)
    assert any("DUCK" in p for p in out)
