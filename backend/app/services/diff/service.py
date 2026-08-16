from collections.abc import Sequence

from app.services.diff.base import DiffEntry, DISPOSITIONS, EMPHASIZED, HELD, MERGED, REMOVED
from app.services.renderer.clean import REMOVABLE_LABELS
from app.services.selection.rules import classify_shape, score_passage

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
    segment_texts: dict[str, str] | None = None,
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
                **_disposition(carrying, removal_reasons.get(segment_id), segment_id in slot_segment_ids, (segment_texts or {}).get(segment_id, getattr(segment, "text", ""))),
            )
        )
    return entries


def _held_reason(segment_text: str, has_slot: bool) -> str:
    """Name the ground the rule layer found, rather than reporting an absence.

    "No semantic content was extracted" repeated down a page tells the reader nothing about
    their document. The rules can say the passage is a table of contents, a flattened
    table, or a generality — something a reader can check.
    """
    rule = score_passage(segment_text, classify_shape(segment_text))
    grounds = [reason for reason in rule.reasons if reason != "본문 서술"]
    if grounds:
        return f"{', '.join(grounds)} — 핵심으로 선택되지 않음"
    if has_slot:
        return "핵심으로 선택되지 않음"
    # Naming what the rules looked for lets the reader check the call; reporting an
    # absence ("핵심 문장을 찾지 못함") gives them nothing to check.
    return "지시·결론·주의·수치 근거가 없는 서술"


def _disposition(
    carrying: list[tuple[str, set[str]]],
    removal_reason: str | None,
    has_slot: bool,
    segment_text: str = "",
) -> dict[str, str]:
    """Read the disposition off what the output did, using labels only for wording."""
    if carrying:
        heading, segment_ids = carrying[0]
        if len(segment_ids) > 1:
            others = len(segment_ids) - 1
            return {"disposition": MERGED, "reason": f"'{heading}' 아래 다른 {others}개 문단과 함께 정리됨"}
        return {"disposition": EMPHASIZED, "reason": f"'{heading}' 항목으로 그대로 유지됨"}
    if removal_reason:
        return {"disposition": REMOVED, "reason": removal_reason}
    return {"disposition": HELD, "reason": _held_reason(segment_text, has_slot)}


def count_dispositions(entries: Sequence[DiffEntry]) -> dict[str, int]:
    counts = dict.fromkeys(DISPOSITIONS, 0)
    for entry in entries:
        counts[entry.disposition] += 1
    return counts
