from collections.abc import Sequence

from app.services.renderer.base import ITEM_BUDGETS, RenderedDocument, make_section, select_by_importance, slot_value
from app.services.renderer.outline import DocumentOutline

REMOVABLE_LABELS = {"REDUNDANT", "GENERIC", "RHETORICAL", "UNSUPPORTED", "OFF_PURPOSE"}
# Fallback grouping for sources that carry no headings of their own.
HEADINGS = (
    ("Problem", {"PROBLEM"}),
    ("Decision", {"DECISION", "RECOMMENDATION"}),
    ("Options and trade-offs", {"OPTION", "TRADE_OFF"}),
    ("Actions", {"ACTION", "OWNER", "DEADLINE", "PRIORITY"}),
    ("Evidence", {"FACT", "EVIDENCE", "SOURCE"}),
    ("Success criteria", {"SUCCESS_CRITERIA"}),
    ("Risks and unknowns", {"RISK_UNKNOWN"}),
)


def _value(value: object) -> str:
    return getattr(value, "value", str(value))


def render_clean_version(slots: Sequence[object], quality_labels: Sequence[object] = (), outline: DocumentOutline | None = None) -> RenderedDocument:
    """The source document with the low-signal material taken out.

    When the source has headings of its own, the condensed document keeps them and their
    order, so it reads as a shorter version of the same document rather than as the same
    content re-filed under an analysis taxonomy. Removal reasons are not written into the
    document; they belong to the rewrite rationale shown beside it.
    """
    removed_segment_ids = {getattr(label, "segment_id") for label in quality_labels if _value(getattr(label, "label")) in REMOVABLE_LABELS}
    kept_slots = [slot for slot in slots if getattr(slot, "source_segment_id", None) not in removed_segment_ids]
    shortlist = select_by_importance(kept_slots, limit=ITEM_BUDGETS["clean_version"], preserve_order=True)

    sections = _source_sections(shortlist, outline) if outline and outline.ordered_headings else _slot_type_sections(shortlist)
    return RenderedDocument(output_type="clean_version", sections=sections)


def _source_sections(shortlist: Sequence[object], outline: DocumentOutline) -> list:
    grouped: dict[str, list[object]] = {}
    for slot in shortlist:
        heading = outline.heading_for(getattr(slot, "source_segment_id", "")) or "그 밖의 내용"
        grouped.setdefault(heading, []).append(slot)
    # Sorted by where each group's first item sits in the source, so material that precedes
    # the first heading — a cover page, a preamble — stays at the front.
    ordered = sorted(grouped, key=lambda heading: min(outline.position_of(getattr(slot, "source_segment_id", "")) for slot in grouped[heading]))
    return [section for heading in ordered if (section := make_section(heading, grouped[heading]))]


def _slot_type_sections(shortlist: Sequence[object]) -> list:
    sections = []
    grouped = set()
    for heading, types in HEADINGS:
        selected = [slot for slot in shortlist if slot_value(slot) in types]
        if section := make_section(heading, selected):
            sections.append(section)
            grouped.update(map(id, selected))
    if (rest := [slot for slot in shortlist if id(slot) not in grouped]) and (section := make_section("Context", rest)):
        sections.append(section)
    return sections
