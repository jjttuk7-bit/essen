from collections.abc import Sequence

from app.services.renderer.base import ITEM_BUDGETS, RenderedDocument, make_section, select_by_importance, slot_value

HEADINGS = (("Decision", {"DECISION", "RECOMMENDATION", "OPTION", "TRADE_OFF"}), ("Actions", {"ACTION"}), ("Owner", {"OWNER"}), ("Deadline", {"DEADLINE"}), ("Success criteria", {"SUCCESS_CRITERIA"}), ("Unknowns", {"RISK_UNKNOWN"}))
ACTIONABLE = {slot_type for _, types in HEADINGS for slot_type in types}


def render_action_decision_sheet(slots: Sequence[object]) -> RenderedDocument:
    # This sheet answers "what do we do", so anything outside the actionable slot types is
    # dropped before ranking rather than kept as filler.
    actionable = [slot for slot in slots if slot_value(slot) in ACTIONABLE]
    kept = set(map(id, select_by_importance(actionable or slots, limit=ITEM_BUDGETS["action_decision_sheet"])))
    shortlist = [slot for slot in (actionable or slots) if id(slot) in kept]

    sections = []
    for heading, types in HEADINGS:
        if section := make_section(heading, [slot for slot in shortlist if slot_value(slot) in types]):
            sections.append(section)
    if not sections and (section := make_section("Open items", shortlist)):
        sections.append(section)
    return RenderedDocument(output_type="action_decision_sheet", sections=sections)
