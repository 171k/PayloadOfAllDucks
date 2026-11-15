"""Exporter and output-correctness tests."""

from __future__ import annotations

import pytest

from poad.core import exporter, generator
from poad.core.generator import Unit


def make_result(values):
    units = [Unit(value=v, transforms=()) for v in values]
    return generator.generate(units, encodings="raw")


def test_txt_one_payload_per_line():
    result = make_result(["a", "b", "c"])
    body = exporter.render_txt(result)
    assert body == "a\nb\nc\n"


def test_txt_no_banner_or_comments():
    result = make_result(["/etc/passwd", "../etc/passwd"])
    body = exporter.render_txt(result)
    assert "PAYLOAD OF ALL DUCKS" not in body
    assert not body.startswith("#")
    assert "POAD" not in body


def test_no_duplicates_in_output():
    result = make_result(["x", "x", "y"])
    assert result.payloads == ["x", "y"]


def test_no_crlf_in_lines():
    result = make_result(["a", "b"])
    body = exporter.render_txt(result)
    assert "\r" not in body


def test_embedded_newline_unit_dropped():
    # A unit whose value contains a newline must not corrupt the TXT list.
    units = [Unit(value="good", transforms=()), Unit(value="bad\nline", transforms=())]
    result = generator.generate(units, encodings="raw")
    assert "good" in result.payloads
    assert "bad\nline" not in result.payloads
    assert result.stats["skipped_invalid"] == 1


def test_no_trailing_whitespace_added():
    result = make_result(["payload"])
    body = exporter.render_txt(result)
    assert body == "payload\n"


def test_empty_result():
    result = make_result([])
    assert exporter.render_txt(result) == ""


def test_deterministic_render():
    r1 = make_result(["b", "a", "c"])
    r2 = make_result(["b", "a", "c"])
    assert exporter.render_txt(r1) == exporter.render_txt(r2)


def test_overwrite_protection(tmp_path):
    result = make_result(["x"])
    out = tmp_path / "payloadlist.txt"
    exporter.write_output(result, out)
    with pytest.raises(exporter.ExportError):
        exporter.write_output(result, out)  # exists, no overwrite
    exporter.write_output(result, out, overwrite=True)  # ok


def test_json_csv_md_formats():
    result = make_result(["a", "b"])
    assert '"payloads"' in exporter.render_json(result)
    assert "value,family" in exporter.render_csv(result)
    assert "# POAD" in exporter.render_markdown(result, title="POAD x")


def test_large_list(tmp_path):
    values = [f"p{i}" for i in range(5000)]
    result = make_result(values)
    out = tmp_path / "big.txt"
    exporter.write_output(result, out)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5000


def test_cap_enforced():
    values = [f"p{i}" for i in range(100)]
    units = [Unit(value=v, transforms=()) for v in values]
    result = generator.generate(units, encodings="raw", max_payloads=10)
    assert result.stats["final_payloads"] == 10
    assert result.warnings
