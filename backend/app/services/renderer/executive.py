from collections.abc import Sequence

from app.services.renderer.base import ITEM_BUDGETS, RenderedDocument, make_section, slot_value
from app.services.selection.hybrid import select_core

HEADINGS = (("Conclusion", {"DECISION", "RECOMMENDATION"}), ("Evidence", {"EVIDENCE", "FACT"}), ("Risk and unknowns", {"RISK_UNKNOWN"}), ("Pending decision", {"OPTION", "TRADE_OFF"}))


def render_executive_summary(slots: Sequence[object], segment_texts: dict[str, str] | None = None) -> RenderedDocument:
    # Ranked across the whole document first, so the budget is spent on the strongest
    # material rather than on whichever heading happens to come first.
    # These forms reorganize by purpose, so no outline coverage constraint applies.
    kept = set(map(id, (item.slot for item in select_core(slots, segment_texts=segment_texts or {}, outline=None, budget=ITEM_BUDGETS["executive_summary"]))))
    shortlist = [slot for slot in slots if id(slot) in kept]

    sections = []
    for heading, types in HEADINGS:
        if section := make_section(heading, [slot for slot in shortlist if slot_value(slot) in types]):
            sections.append(section)
    if not sections and (section := make_section("Summary", shortlist)):
        sections.append(section)
    return RenderedDocument(output_type="executive_summary", sections=sections)
