from collections.abc import Sequence

from app.services.diff.base import DiffEntry, DISPOSITIONS, EMPHASIZED, HELD, MERGED, REMOVED
from app.services.renderer.clean import REMOVABLE_LABELS

REMOVED_HEADING = "Removed candidates"


def _value(value: object) -> str:
    return getattr(value, "value", str(value))


def _surviving_sections(provenance: Sequence[dict[str, object]]) -> dict[int, tuple[str, set[str]]]:
    """Group provenance into sections that actually carry content into the output.

    The clean renderer files dropped material under a "Removed candidates" heading, which
    documents a deletion rather than surviving text, so those sections are excluded here.
    """
    sections: dict[int, tuple[str, set[str]]] = {}
    for reference in provenance:
        heading = str(reference.get("heading", ""))
        if heading == REMOVED_HEADING:
            continue
        index = int(reference.get("section_index", 0))
        _, segment_ids = sections.setdefault(index, (heading, set()))
        segment_ids.add(str(reference["source_segment_id"]))
    return sections


def build_diff(
    segments: Sequence[object],
    quality_labels: Sequence[object] = (),
    provenance: Sequence[dict[str, object]] = (),
) -> list[DiffEntry]:
    """Explain, per source segment, what the rendered output did with it and why."""
    sections = _surviving_sections(provenance)
    removal_reasons = {
        getattr(label, "segment_id"): getattr(label, "reason")
        for label in quality_labels
        if _value(getattr(label, "label")) in REMOVABLE_LABELS
    }
    slot_segment_ids = {str(reference["source_segment_id"]) for reference in provenance}

    entries: list[DiffEntry] = []
    for segment in sorted(segments, key=lambda segment: getattr(segment, "order_index")):
        segment_id = getattr(segment, "id")
        carrying = [(heading, segment_ids) for heading, segment_ids in sections.values() if segment_id in segment_ids]
        entries.append(
            DiffEntry(
                segment_id=segment_id,
                order_index=getattr(segment, "order_index"),
                original_text=getattr(segment, "text"),
                rendered_headings=tuple(heading for heading, _ in carrying),
                **_disposition(carrying, removal_reasons.get(segment_id), segment_id in slot_segment_ids),
            )
        )
    return entries


def _disposition(
    carrying: list[tuple[str, set[str]]],
    removal_reason: str | None,
    has_slot: bool,
) -> dict[str, str]:
    """Read the disposition off what the output did, using labels only for wording."""
    if carrying:
        heading, segment_ids = carrying[0]
        if len(segment_ids) > 1:
            others = len(segment_ids) - 1
            return {"disposition": MERGED, "reason": f"Combined with {others} other source segment{'s' if others > 1 else ''} under '{heading}'."}
        return {"disposition": EMPHASIZED, "reason": f"Carried into the output as its own section under '{heading}'."}
    if removal_reason:
        return {"disposition": REMOVED, "reason": removal_reason}
    if has_slot:
        return {"disposition": HELD, "reason": "Extracted content was not selected for this output."}
    return {"disposition": HELD, "reason": "No semantic content was extracted from this segment."}


def count_dispositions(entries: Sequence[DiffEntry]) -> dict[str, int]:
    counts = dict.fromkeys(DISPOSITIONS, 0)
    for entry in entries:
        counts[entry.disposition] += 1
    return counts
