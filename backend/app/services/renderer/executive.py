from collections.abc import Sequence
from app.services.renderer.base import RenderedDocument, make_section, slot_value

HEADINGS = (("Conclusion", {"DECISION", "RECOMMENDATION"}), ("Evidence", {"EVIDENCE", "FACT"}), ("Risk and unknowns", {"RISK_UNKNOWN"}), ("Pending decision", {"OPTION", "TRADE_OFF"}))


def render_executive_summary(slots: Sequence[object]) -> RenderedDocument:
    remaining = list(slots)
    sections = []
    for heading, types in HEADINGS:
        selected = [slot for slot in remaining if slot_value(slot) in types]
        if section := make_section(heading, selected):
            sections.append(section)
            remaining = [slot for slot in remaining if slot not in selected]
    if remaining and (section := make_section("Source-backed details", remaining)):
        sections.append(section)
    return RenderedDocument(output_type="executive_summary", sections=sections)
