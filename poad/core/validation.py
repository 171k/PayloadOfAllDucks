"""Input and output validation helpers.

These are intentionally strict: POAD produces wordlists that get loaded verbatim
into tools like Burp Intruder, so a malformed line (embedded newline, trailing
whitespace the generator added, etc.) is a correctness bug, not a cosmetic one.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath


class ValidationError(ValueError):
    """Raised for invalid user input."""


# Characters that must never appear inside a single payload line for TXT export.
_FORBIDDEN_LINE_CHARS = ("\n", "\r")


def is_valid_line(payload: str) -> bool:
    """True if ``payload`` is a single, exportable TXT line."""
    if payload == "":
        return False
    return not any(c in payload for c in _FORBIDDEN_LINE_CHARS)


def validate_depth(depth: int, *, maximum: int = 64) -> int:
    if not isinstance(depth, int):
        raise ValidationError("Depth must be an integer")
    if depth < 0:
        raise ValidationError("Depth must be >= 0")
    if depth > maximum:
        raise ValidationError(f"Depth must be <= {maximum}")
    return depth


def validate_nonempty(value: str, *, field: str) -> str:
    if value is None or str(value).strip() == "":
        raise ValidationError(f"{field} must not be empty")
    if any(c in value for c in _FORBIDDEN_LINE_CHARS):
        raise ValidationError(f"{field} must not contain newline characters")
    return value


def normalise_unix_path(path: str) -> str:
    """Return a cleaned absolute-looking POSIX path (collapses duplicate slashes).

    This does NOT resolve against the real filesystem (the target file usually
    does not exist locally); it only normalises the string form.
    """
    validate_nonempty(path, field="Target file")
    # Preserve leading slash semantics; collapse runs of slashes.
    p = PurePosixPath(path)
    cleaned = str(p)
    if path.startswith("/") and not cleaned.startswith("/"):
        cleaned = "/" + cleaned
    return cleaned


def relative_unix_path(path: str) -> str:
    """Strip a single leading slash so a traversal prefix can be prepended."""
    return normalise_unix_path(path).lstrip("/")


def normalise_windows_path(path: str) -> str:
    validate_nonempty(path, field="Target file")
    return str(PureWindowsPath(path))


def resource_within(base: Path, candidate: Path) -> bool:
    """True if ``candidate`` resolves to a location inside ``base``.

    Used by importers to refuse template/wordlist paths that escape an expected
    directory via ``..`` traversal.
    """
    try:
        base_r = base.resolve()
        cand_r = candidate.resolve()
    except OSError:  # pragma: no cover - defensive
        return False
    return base_r == cand_r or base_r in cand_r.parents
