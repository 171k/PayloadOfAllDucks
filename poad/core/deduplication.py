"""Order-preserving de-duplication."""

from __future__ import annotations

from typing import Iterable, TypeVar

T = TypeVar("T")


def dedupe(items: Iterable[str]) -> tuple[list[str], int]:
    """Return (unique_items_in_first_seen_order, removed_count)."""
    seen: set[str] = set()
    unique: list[str] = []
    removed = 0
    for item in items:
        if item in seen:
            removed += 1
            continue
        seen.add(item)
        unique.append(item)
    return unique, removed


def dedupe_keyed(items: Iterable[T], key) -> tuple[list[T], int]:
    """De-dupe by ``key(item)`` while preserving the first occurrence of each key."""
    seen: set = set()
    unique: list[T] = []
    removed = 0
    for item in items:
        k = key(item)
        if k in seen:
            removed += 1
            continue
        seen.add(k)
        unique.append(item)
    return unique, removed
