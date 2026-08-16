from collections.abc import Sequence

from app.services.renderer.base import ITEM_BUDGETS, RenderedDocument, make_section, select_by_importance, slot_value

HEADINGS = (("Conclusion", {"DECISION", "RECOMMENDATION"}), ("Evidence", {"EVIDENCE", "FACT"}), ("Risk and unknowns", {"RISK_UNKNOWN"}), ("Pending decision", {"OPTION", "TRADE_OFF"}))


def render_executive_summary(slots: Sequence[object]) -> RenderedDocument:
    # Ranked across the whole document first, so the budget is spent on the strongest
    # material rather than on whichever heading happens to come first.
    kept = set(map(id, select_by_importance(slots, limit=ITEM_BUDGETS["executive_summary"])))
    shortlist = [slot for slot in slots if id(slot) in kept]

    sections = []
    for heading, types in HEADINGS:
        if section := make_section(heading, [slot for slot in shortlist if slot_value(slot) in types]):
            sections.append(section)
    if not sections and (section := make_section("Summary", shortlist)):
        sections.append(section)
    return RenderedDocument(output_type="executive_summary", sections=sections)
