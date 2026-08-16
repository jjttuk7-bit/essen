from collections.abc import Sequence

from app.services.renderer.base import ITEM_BUDGETS, RenderedDocument, make_section, slot_value
from app.services.selection.hybrid import select_core

HEADINGS = (("Decision", {"DECISION", "RECOMMENDATION", "OPTION", "TRADE_OFF"}), ("Actions", {"ACTION"}), ("Owner", {"OWNER"}), ("Deadline", {"DEADLINE"}), ("Success criteria", {"SUCCESS_CRITERIA"}), ("Unknowns", {"RISK_UNKNOWN"}))
ACTIONABLE = {slot_type for _, types in HEADINGS for slot_type in types}


def render_action_decision_sheet(slots: Sequence[object], segment_texts: dict[str, str] | None = None) -> RenderedDocument:
    # This sheet answers "what do we do", so anything outside the actionable slot types is
    # dropped before ranking rather than kept as filler.
    actionable = [slot for slot in slots if slot_value(slot) in ACTIONABLE]
    # These forms reorganize by purpose, so no outline coverage constraint applies.
    kept = set(map(id, (item.slot for item in select_core(actionable or slots, segment_texts=segment_texts or {}, outline=None, budget=ITEM_BUDGETS["action_decision_sheet"]))))
    shortlist = [slot for slot in (actionable or slots) if id(slot) in kept]

    sections = []
    for heading, types in HEADINGS:
        if section := make_section(heading, [slot for slot in shortlist if slot_value(slot) in types]):
            sections.append(section)
    if not sections and (section := make_section("Open items", shortlist)):
        sections.append(section)
    return RenderedDocument(output_type="action_decision_sheet", sections=sections)
