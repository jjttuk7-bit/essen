from collections.abc import Sequence

from app.services.renderer.base import ITEM_BUDGETS, RenderedDocument, make_section, slot_value
from app.services.renderer.outline import DocumentOutline
from app.services.selection.hybrid import select_core

REMOVABLE_LABELS = {"REDUNDANT", "GENERIC", "RHETORICAL", "UNSUPPORTED", "OFF_PURPOSE"}
# The reader should learn what the document says before reading the document.
KEY_POINTS = 3
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


def render_clean_version(slots: Sequence[object], quality_labels: Sequence[object] = (), outline: DocumentOutline | None = None, segment_texts: dict[str, str] | None = None, shown_elsewhere: Sequence[str] = ()) -> RenderedDocument:
    """The source document with the low-signal material taken out.

    When the source has headings of its own, the condensed document keeps them and their
    order, so it reads as a shorter version of the same document rather than as the same
    content re-filed under an analysis taxonomy. Removal reasons are not written into the
    document; they belong to the rewrite rationale shown beside it.
    """
    removed_segment_ids = {getattr(label, "segment_id") for label in quality_labels if _value(getattr(label, "label")) in REMOVABLE_LABELS}
    # Removing repetition is what this product is for, so it cannot repeat a line the page
    # has already shown — the identity block quotes the document's purpose above the body.
    already_shown = {" ".join(text.split()) for text in shown_elsewhere if text}
    kept_slots = [
        slot for slot in slots
        if getattr(slot, "source_segment_id", None) not in removed_segment_ids
        and " ".join(getattr(slot, "normalized_text", "").split()) not in already_shown
    ]
    # The clean version is the same document made shorter, so selection carries the
    # outline: every source section that has a candidate keeps at least one.
    selections = select_core(kept_slots, segment_texts=segment_texts or {}, outline=outline, budget=ITEM_BUDGETS["clean_version"])
    shortlist = [item.slot for item in selections]

    sections = _source_sections(shortlist, outline) if outline and outline.ordered_headings else _slot_type_sections(shortlist)
    if opening := _key_points(selections):
        sections.insert(0, opening)
    return RenderedDocument(output_type="clean_version", sections=sections)


def _key_points(selections: Sequence[object]) -> object | None:
    """Open with the document's strongest lines, so the core arrives before the document.

    These are quoted, not written: the same passages the body carries, lifted to the front.
    They stay in the body too — a summary that removed its own lines from the document
    would leave the reader holding two half-documents.
    """
    strongest = sorted(selections, key=lambda item: -getattr(item, "score", 0.0))[:KEY_POINTS]
    if not strongest:
        return None
    ordered = [item.slot for item in sorted(strongest, key=lambda item: selections.index(item))]
    return make_section(f"핵심 {len(ordered)}줄", ordered)


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
