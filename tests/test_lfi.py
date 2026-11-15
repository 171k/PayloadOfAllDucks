"""Path Traversal / LFI module tests."""

from __future__ import annotations

import pytest

from poad.core import generator
from poad.modules import get_module
from poad.modules.base import ModuleError, resolve_encoding


def gen(ctx, encoding="all"):
    module = get_module("lfi")
    build = module.build(ctx, None)  # LFI ignores the library
    result = generator.generate(build.units, encodings=resolve_encoding(encoding))
    return result.payloads


def test_absolute_and_relative_linux():
    payloads = gen({"file": "/flag/flag.txt", "os": "linux", "depth": 4})
    assert "/flag/flag.txt" in payloads
    assert "flag/flag.txt" in payloads


def test_relative_traversal_depths():
    payloads = gen({"file": "/flag/flag.txt", "os": "linux", "depth": 4})
    assert "../flag/flag.txt" in payloads
    assert "../../flag/flag.txt" in payloads
    assert "../../../../flag/flag.txt" in payloads
    # Depth is respected: no 5-deep traversal when depth=4.
    assert "../../../../../flag/flag.txt" not in payloads


def test_encoded_separators():
    payloads = gen({"file": "/flag/flag.txt", "os": "linux", "depth": 2})
    assert "..%2fflag%2fflag.txt" in payloads
    assert "..%2f..%2fflag%2fflag.txt" in payloads


def test_double_encoded_separators():
    payloads = gen({"file": "/flag/flag.txt", "os": "linux", "depth": 2})
    assert "..%252fflag%252fflag.txt" in payloads


def test_no_malformed_absolute_concatenation():
    # Traversal variants must never contain '../' glued onto an absolute path.
    payloads = gen({"file": "/flag/flag.txt", "os": "linux", "depth": 3})
    assert not any(p.startswith("../") and "/flag/flag.txt" in p and p.count("//") for p in payloads)
    assert ".../flag" not in "".join(payloads)


def test_windows_backslash_and_drive():
    payloads = gen({"file": "C:\\Windows\\win.ini", "os": "windows", "depth": 2})
    assert "C:\\Windows\\win.ini" in payloads
    assert "Windows\\win.ini" in payloads
    assert "..\\Windows\\win.ini" in payloads
    assert "..\\..\\Windows\\win.ini" in payloads


def test_windows_encoded_backslash():
    payloads = gen({"file": "C:\\Windows\\win.ini", "os": "windows", "depth": 1})
    assert "..%5cWindows%5cwin.ini" in payloads


def test_encoding_raw_only():
    payloads = gen({"file": "/a/b", "os": "linux", "depth": 1}, encoding="raw")
    assert all("%" not in p for p in payloads)
    assert "../a/b" in payloads


def test_dedup_no_duplicates():
    payloads = gen({"file": "/flag/flag.txt", "os": "linux", "depth": 8})
    assert len(payloads) == len(set(payloads))


def test_prefix_suffix():
    payloads = gen({
        "file": "/etc/passwd", "os": "linux", "depth": 1,
        "families": ["direct"], "prefix": "page=", "suffix": "%00",
    }, encoding="raw")
    assert "page=/etc/passwd%00" in payloads
    assert "page=etc/passwd%00" in payloads


def test_null_byte_variants():
    payloads = gen({
        "file": "/etc/passwd", "os": "linux", "depth": 1,
        "families": ["direct"], "null_byte": True,
    }, encoding="raw")
    assert any(p.endswith("%00") for p in payloads)


def test_non_ascii_filename():
    payloads = gen({"file": "/flag/flág.txt", "os": "linux", "depth": 1}, encoding="raw")
    assert "/flag/flág.txt" in payloads
    assert "../flag/flág.txt" in payloads


def test_empty_path_rejected():
    module = get_module("lfi")
    with pytest.raises(ModuleError):
        module.build({"file": "/", "os": "linux", "depth": 1}, None)


def test_depth_zero_direct_only():
    payloads = gen({"file": "/a/b", "os": "linux", "depth": 0, "families": ["traversal"]})
    # depth 0 => no traversal units at all
    assert payloads == [] or all("../" not in p for p in payloads)


def test_deterministic_output():
    a = gen({"file": "/flag/flag.txt", "os": "linux", "depth": 6})
    b = gen({"file": "/flag/flag.txt", "os": "linux", "depth": 6})
    assert a == b


def test_bad_family_rejected():
    module = get_module("lfi")
    with pytest.raises(ModuleError):
        module.build({"file": "/a", "os": "linux", "families": ["nope"]}, None)
