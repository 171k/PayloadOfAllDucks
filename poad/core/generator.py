"""The generation pipeline.

Pipeline order (also documented in the README):

1. A module builds *units* (templates already substituted with user context).
2. Each unit's compatible transforms are filtered by the user's encoding choice.
3. Transforms are applied to produce variants.
4. Variants that are not valid single TXT lines are dropped (and counted).
5. Duplicates are removed (first occurrence wins).
6. A hard cap is applied to avoid combinatorial explosions.
7. Deterministic ordering is preserved (insertion order; optional alpha sort).

The same inputs + version + template library always produce identical output.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from poad.core import deduplication, transformations, validation


@dataclass(frozen=True)
class Unit:
    """A fully-substituted base payload plus the transforms that are safe for it."""

    value: str
    transforms: tuple[str, ...] = ()
    family: str = ""
    template_id: str = ""
    note: str | None = None


@dataclass(frozen=True)
class PayloadRecord:
    value: str
    family: str
    template_id: str
    transform: str
    note: str | None = None


@dataclass
class GenerationResult:
    records: list[PayloadRecord] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    info: dict[str, object] = field(default_factory=dict)

    @property
    def payloads(self) -> list[str]:
        return [r.value for r in self.records]


def _selected_transforms(encodings) -> set[str] | None:
    """Translate an encoding selection into a set of transform names (or None=all).

    Accepted values:
      * ``"all"`` / ``None``        -> every transform a unit declares compatible
      * ``"raw"`` / ``"none"``      -> no transforms (raw base only)
      * a transform name string     -> just that transform (plus raw base)
      * an iterable of names        -> exactly those transforms (plus raw base)
    """
    if encodings is None or encodings == "all":
        return None
    if isinstance(encodings, str):
        if encodings in ("raw", "none"):
            return set()
        return {encodings}
    return set(encodings)


def generate(
    units: list[Unit],
    *,
    encodings="all",
    max_payloads: int = 50000,
    include_raw: bool = True,
    sort: bool = False,
) -> GenerationResult:
    """Run the pipeline over ``units`` and return a :class:`GenerationResult`."""
    selected = _selected_transforms(encodings)

    expanded: list[PayloadRecord] = []
    skipped_invalid = 0
    template_ids: set[str] = set()

    for unit in units:
        if unit.template_id:
            template_ids.add(unit.template_id)

        variants: list[tuple[str, str]] = []
        if include_raw:
            variants.append((unit.value, "raw"))

        for tname in unit.transforms:
            if selected is None or tname in selected:
                try:
                    tv = transformations.apply(tname, unit.value)
                except KeyError:
                    continue
                variants.append((tv, tname))

        # If raw was excluded but no transforms selected, still emit the base so
        # the unit is not silently lost.
        if not variants:
            variants.append((unit.value, "raw"))

        for value, tname in variants:
            if not validation.is_valid_line(value):
                skipped_invalid += 1
                continue
            expanded.append(
                PayloadRecord(
                    value=value,
                    family=unit.family,
                    template_id=unit.template_id,
                    transform=tname,
                    note=unit.note,
                )
            )

    variants_generated = len(expanded)

    unique_records, removed = deduplication.dedupe_keyed(expanded, key=lambda r: r.value)

    capped = False
    if len(unique_records) > max_payloads:
        unique_records = unique_records[:max_payloads]
        capped = True

    if sort:
        unique_records.sort(key=lambda r: r.value)

    stats = {
        "templates_loaded": len(template_ids),
        "units": len(units),
        "variants_generated": variants_generated,
        "duplicates_removed": removed,
        "skipped_invalid": skipped_invalid,
        "final_payloads": len(unique_records),
    }

    result = GenerationResult(records=unique_records, stats=stats)
    if capped:
        result.warnings.append(
            f"Output capped at max_payloads={max_payloads}. "
            "Raise the cap or narrow your selection for a complete list."
        )
    return result
