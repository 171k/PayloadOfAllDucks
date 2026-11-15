"""Import a plaintext wordlist into a POAD template pack.

Each non-empty, non-comment line becomes one literal template. Lines are
de-duplicated and lines that are not valid single export lines are skipped and
reported. Nothing is executed or evaluated.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from poad.core.deduplication import dedupe
from poad.core.template_engine import Template, TemplatePack
from poad.core.validation import is_valid_line


@dataclass
class ImportStats:
    imported: int = 0
    skipped_blank: int = 0
    skipped_invalid: int = 0
    duplicates: int = 0


def import_wordlist(
    path: str | Path,
    category: str,
    *,
    source_label: str | None = None,
    comment_prefix: str = "#",
) -> tuple[TemplatePack, ImportStats]:
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    stats = ImportStats()
    raw_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.rstrip("\r")
        if stripped.strip() == "":
            stats.skipped_blank += 1
            continue
        if comment_prefix and stripped.lstrip().startswith(comment_prefix):
            continue
        if not is_valid_line(stripped):
            stats.skipped_invalid += 1
            continue
        raw_lines.append(stripped)

    unique, removed = dedupe(raw_lines)
    stats.duplicates = removed
    stats.imported = len(unique)

    source = source_label or f"imported:{p.name}"
    templates = [
        Template(
            id=f"import-{category}-{i:05d}",
            name=f"imported {category} #{i}",
            category=category,
            template=line,
            tags=("imported",),
            source=source,
        )
        for i, line in enumerate(unique)
    ]
    pack = TemplatePack(
        name=f"imported-{category}-{p.stem}",
        category=category,
        source=source,
        templates=templates,
    )
    return pack, stats
