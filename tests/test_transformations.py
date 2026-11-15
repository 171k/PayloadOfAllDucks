"""Byte-exact tests for the transformation engine."""

from __future__ import annotations

from poad.core import transformations as T


def test_raw_is_identity():
    for s in ["{{7*7}}", "a+b", 'q"u\'ote', "back\\slash", "/etc/passwd"]:
        assert T.raw(s) == s


def test_url_sep_lowercase():
    assert T.url_sep("/etc/passwd") == "%2fetc%2fpasswd"
    assert T.url_sep("a\\b") == "a%5cb"


def test_url_sep_upper():
    assert T.url_sep_upper("/a") == "%2Fa"
    assert T.url_sep_upper("a\\b") == "a%5Cb"


def test_double_url_sep():
    assert T.double_url_sep("/a") == "%252fa"
    assert T.double_url_sep("a\\b") == "a%255cb"


def test_url_all_preserves_unreserved():
    assert T.url_all("abcXYZ0129-._~") == "abcXYZ0129-._~"


def test_url_all_encodes_reserved_uppercase_hex():
    assert T.url_all("a b") == "a%20b"
    assert T.url_all("<>") == "%3C%3E"
    assert T.url_all("/") == "%2F"


def test_url_all_double():
    assert T.url_all_double("a b") == "a%2520b"


def test_overlong_utf8_sep():
    assert T.overlong_utf8_sep("/") == "%c0%af"


def test_html_entity_named():
    assert T.html_entity("<script>") == "&lt;script&gt;"
    assert T.html_entity('a&b"c\'d') == "a&amp;b&quot;c&#39;d"


def test_html_entity_preserves_braces():
    # SSTI payloads must survive HTML entity encoding of unrelated chars.
    assert T.html_entity("{{7*7}}") == "{{7*7}}"


def test_html_entity_hex_and_decimal():
    assert T.html_entity_hex("<") == "&#x3c;"
    assert T.html_entity_decimal("<") == "&#60;"


def test_registry_apply():
    assert T.apply("url_sep", "/a") == "%2fa"
    assert set(["raw", "url_sep", "double_url_sep"]).issubset(set(T.available()))


def test_no_accidental_decode_then_reencode():
    # An existing percent-encoding must be preserved, not decoded and re-encoded.
    assert T.url_sep("a%2fb") == "a%2fb"  # no slash to touch
    assert T.raw("%2e%2e/") == "%2e%2e/"
