from collections.abc import Sequence

from app.services.renderer.base import ITEM_BUDGETS, RenderedDocument, make_section, select_by_importance, slot_value

REMOVABLE_LABELS = {"REDUNDANT", "GENERIC", "RHETORICAL", "UNSUPPORTED", "OFF_PURPOSE"}
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


def render_clean_version(slots: Sequence[object], quality_labels: Sequence[object] = ()) -> RenderedDocument:
    """The source document with the low-signal material taken out.

    Removal reasons are not written into the document itself — they belong to the rewrite
    rationale shown beside it, so the document stays readable on its own.
    """
    removed_segment_ids = {getattr(label, "segment_id") for label in quality_labels if _value(getattr(label, "label")) in REMOVABLE_LABELS}
    kept_slots = [slot for slot in slots if getattr(slot, "source_segment_id", None) not in removed_segment_ids]
    shortlist = select_by_importance(kept_slots, limit=ITEM_BUDGETS["clean_version"], preserve_order=True)

    sections = []
    grouped = set()
    for heading, types in HEADINGS:
        selected = [slot for slot in shortlist if slot_value(slot) in types]
        if section := make_section(heading, selected):
            sections.append(section)
            grouped.update(map(id, selected))
    if (rest := [slot for slot in shortlist if id(slot) not in grouped]) and (section := make_section("Context", rest)):
        sections.append(section)
    return RenderedDocument(output_type="clean_version", sections=sections)
