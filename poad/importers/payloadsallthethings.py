"""Import payloads from a *local* PayloadsAllTheThings checkout.

PayloadsAllTheThings (https://github.com/swisskyrepo/PayloadsAllTheThings) is an
MIT-licensed collection. This importer:

* Reads only from a local directory you already have (never scrapes GitHub).
* Imports reliable ``.txt`` Intruder wordlists by default; it does not try to
  blindly convert arbitrary Markdown code blocks into payloads.
* Categorises entries by directory name, skipping anything it cannot map.
* Preserves MIT attribution on the generated packs.
* Never executes, evaluates, or tests any payload.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from poad.core.deduplication import dedupe
from poad.core.template_engine import Template, TemplatePack
from poad.core.validation import is_valid_line

# Map a PayloadsAllTheThings top-level folder keyword -> POAD category.
_CATEGORY_KEYWORDS = {
    "directory traversal": "lfi",
    "file inclusion": "lfi",
    "server side template injection": "ssti",
    "sql injection": "sqli",
    "xss injection": "xss",
    "cross site scripting": "xss",
    "command injection": "command_injection",
    "server side request forgery": "ssrf",
    "xxe injection": "xxe",
}

_ATTRIBUTION = (
    "Imported from PayloadsAllTheThings (MIT License), "
    "https://github.com/swisskyrepo/PayloadsAllTheThings"
)


@dataclass
class PattStats:
    files_scanned: int = 0
    files_imported: int = 0
    files_skipped_uncategorised: int = 0
    payloads_imported: int = 0
    payloads_skipped: int = 0
    duplicates: int = 0
    per_category: dict[str, int] = field(default_factory=dict)


def _category_for(path: Path) -> str | None:
    low = str(path).replace("\\", "/").lower()
    for keyword, category in _CATEGORY_KEYWORDS.items():
        if keyword in low:
            return category
    return None


def import_patt(
    root: str | Path,
    *,
    include_txt: bool = True,
) -> tuple[dict[str, TemplatePack], PattStats]:
    base = Path(root)
    if not base.is_dir():
        raise NotADirectoryError(f"Not a directory: {base}")

    stats = PattStats()
    buckets: dict[str, list[str]] = {}

    patterns = ["*.txt"] if include_txt else []
    for pattern in patterns:
        for file_path in sorted(base.rglob(pattern)):
            stats.files_scanned += 1
            category = _category_for(file_path)
            if category is None:
                stats.files_skipped_uncategorised += 1
                continue
            stats.files_imported += 1
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line in text.splitlines():
                s = line.rstrip("\r")
                if s.strip() == "" or s.lstrip().startswith("#"):
                    continue
                if not is_valid_line(s):
                    stats.payloads_skipped += 1
                    continue
                buckets.setdefault(category, []).append(s)

    packs: dict[str, TemplatePack] = {}
    for category, lines in buckets.items():
        unique, removed = dedupe(lines)
        stats.duplicates += removed
        stats.payloads_imported += len(unique)
        stats.per_category[category] = len(unique)
        templates = [
            Template(
                id=f"patt-{category}-{i:05d}",
                name=f"PayloadsAllTheThings {category} #{i}",
                category=category,
                template=line,
                tags=("imported", "payloadsallthethings"),
                source="payloadsallthethings",
            )
            for i, line in enumerate(unique)
        ]
        packs[category] = TemplatePack(
            name=f"patt-{category}",
            category=category,
            source="payloadsallthethings",
            templates=templates,
            license="MIT",
            attribution=_ATTRIBUTION,
        )

    return packs, stats
