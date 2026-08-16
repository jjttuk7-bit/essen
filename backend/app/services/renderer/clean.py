from collections.abc import Sequence

from app.services.renderer.base import RenderedDocument, RenderedSection, make_section

REMOVABLE_LABELS = {"REDUNDANT", "GENERIC", "RHETORICAL", "UNSUPPORTED", "OFF_PURPOSE"}


def _value(value: object) -> str:
    return getattr(value, "value", str(value))


def render_clean_version(slots: Sequence[object], quality_labels: Sequence[object] = ()) -> RenderedDocument:
    removed_segment_ids = {getattr(label, "segment_id") for label in quality_labels if _value(getattr(label, "label")) in REMOVABLE_LABELS}
    kept_slots = [slot for slot in slots if getattr(slot, "source_segment_id", None) not in removed_segment_ids]
    sections = [section for slot in kept_slots if (section := make_section("Source-backed content", [slot]))]
    slots_by_segment = {getattr(slot, "source_segment_id", None): slot for slot in slots}
    for label in quality_labels:
        slot = slots_by_segment.get(getattr(label, "segment_id"))
        if slot is None or _value(getattr(label, "label")) not in REMOVABLE_LABELS:
            continue
        sections.append(RenderedSection("Removed candidates", f"{getattr(label, 'reason')}", [getattr(slot, "id")], [getattr(slot, "source_segment_id")]))
    return RenderedDocument(output_type="clean_version", sections=sections)

