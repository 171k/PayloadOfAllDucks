"""Deterministic payload transformations (encoding variants).

Every transform is a pure ``str -> str`` function. Transforms are applied by the
generator *only* when a template/module declares them compatible, because some
encodings (e.g. URL-encoding an SSTI ``{{7*7}}`` probe) would break the payload.

Design rules (see tests/test_transformations.py for byte-exact expectations):

* Separator encodings use **lowercase** hex (``%2f``) to match common writeups
  and the examples in the project spec.
* Full URL encoding uses **uppercase** hex, matching ``urllib.parse.quote``.
* Transforms never URL-decode first, so intentional existing percent-encodings
  and literal ``+``/backslashes/quotes/braces are preserved exactly.
"""

from __future__ import annotations

from typing import Callable

Transform = Callable[[str], str]

# RFC 3986 unreserved characters are never percent-encoded by url_all.
_UNRESERVED = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
)


def raw(value: str) -> str:
    """Identity transform (the unmodified payload)."""
    return value


def url_sep(value: str) -> str:
    """Encode path separators only: ``/`` -> ``%2f`` and ``\\`` -> ``%5c``."""
    return value.replace("/", "%2f").replace("\\", "%5c")


def url_sep_upper(value: str) -> str:
    """Mixed/upper-case hex separator encoding: ``/`` -> ``%2F``."""
    return value.replace("/", "%2F").replace("\\", "%5C")


def double_url_sep(value: str) -> str:
    """Double-encode path separators: ``/`` -> ``%252f`` and ``\\`` -> ``%255c``."""
    return value.replace("/", "%252f").replace("\\", "%255c")


def overlong_utf8_sep(value: str) -> str:
    """Overlong UTF-8 encoding of ``/`` (``%c0%af``), a classic normalisation bypass.

    This is a well-known traversal variant; it only works against decoders that
    accept non-shortest-form UTF-8. Marked as its own transform so modules can
    opt in explicitly.
    """
    return value.replace("/", "%c0%af").replace("\\", "%c1%9c")


def _percent_encode(value: str, *, safe: str = "") -> str:
    """Percent-encode all bytes outside the unreserved set (UTF-8), uppercase hex."""
    out: list[str] = []
    for ch in value:
        if ch in _UNRESERVED or ch in safe:
            out.append(ch)
        else:
            for byte in ch.encode("utf-8"):
                out.append(f"%{byte:02X}")
    return "".join(out)


def url_all(value: str) -> str:
    """Standard full percent-encoding of every reserved/unsafe character."""
    return _percent_encode(value)


def url_all_double(value: str) -> str:
    """Apply full percent-encoding twice (useful for some traversal filters)."""
    return _percent_encode(_percent_encode(value))


_HTML_NAMED = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
}


def html_entity(value: str) -> str:
    """Encode HTML-significant characters using named/numeric entities."""
    return "".join(_HTML_NAMED.get(ch, ch) for ch in value)


def html_entity_decimal(value: str) -> str:
    """Encode HTML-significant characters as decimal numeric entities."""
    specials = set(_HTML_NAMED)
    return "".join(f"&#{ord(ch)};" if ch in specials else ch for ch in value)


def html_entity_hex(value: str) -> str:
    """Encode HTML-significant characters as hexadecimal numeric entities."""
    specials = set(_HTML_NAMED)
    return "".join(f"&#x{ord(ch):x};" if ch in specials else ch for ch in value)


# Registry: name -> callable. Modules and templates reference transforms by name.
REGISTRY: dict[str, Transform] = {
    "raw": raw,
    "url_sep": url_sep,
    "url_sep_upper": url_sep_upper,
    "double_url_sep": double_url_sep,
    "overlong_utf8_sep": overlong_utf8_sep,
    "url_all": url_all,
    "url_all_double": url_all_double,
    "html_entity": html_entity,
    "html_entity_decimal": html_entity_decimal,
    "html_entity_hex": html_entity_hex,
}

# Human-readable descriptions for help output.
DESCRIPTIONS: dict[str, str] = {
    "raw": "Unmodified payload",
    "url_sep": "URL-encode path separators (/ -> %2f)",
    "url_sep_upper": "URL-encode separators with upper-case hex (/ -> %2F)",
    "double_url_sep": "Double URL-encode separators (/ -> %252f)",
    "overlong_utf8_sep": "Overlong UTF-8 separator (/ -> %c0%af)",
    "url_all": "Full percent-encoding of all reserved characters",
    "url_all_double": "Double full percent-encoding",
    "html_entity": "HTML entity-encode < > & \" '",
    "html_entity_decimal": "HTML decimal numeric entities",
    "html_entity_hex": "HTML hexadecimal numeric entities",
}


def available() -> list[str]:
    return list(REGISTRY.keys())


def apply(name: str, value: str) -> str:
    """Apply a named transform. Raises KeyError for unknown names."""
    try:
        fn = REGISTRY[name]
    except KeyError as exc:  # pragma: no cover - defensive
        raise KeyError(f"Unknown transform: {name!r}") from exc
    return fn(value)
