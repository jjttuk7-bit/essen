from collections.abc import Sequence
from app.services.renderer.base import RenderedDocument, make_section, slot_value

HEADINGS = (("Decision", {"DECISION", "RECOMMENDATION", "OPTION", "TRADE_OFF"}), ("Actions", {"ACTION"}), ("Owner", {"OWNER"}), ("Deadline", {"DEADLINE"}), ("Success criteria", {"SUCCESS_CRITERIA"}), ("Unknowns", {"RISK_UNKNOWN"}))


def render_action_decision_sheet(slots: Sequence[object]) -> RenderedDocument:
    sections = []
    for heading, types in HEADINGS:
        if section := make_section(heading, [slot for slot in slots if slot_value(slot) in types]):
            sections.append(section)
    if not sections and (section := make_section("Source-backed details", slots)):
        sections.append(section)
    return RenderedDocument(output_type="action_decision_sheet", sections=sections)
