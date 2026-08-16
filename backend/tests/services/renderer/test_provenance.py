from types import SimpleNamespace

import pytest

from app.services.renderer.service import RendererService, UnsupportedClaimError


def slot(slot_id: str, slot_type: str, text: str) -> SimpleNamespace:
    return SimpleNamespace(id=slot_id, source_segment_id=f"seg_{slot_id}", slot_type=SimpleNamespace(value=slot_type), normalized_text=text)


def test_every_rendered_section_cites_existing_semantic_slots_and_segments() -> None:
    slots = [
        slot("slot_decision", "DECISION", "Launch the pilot."),
        slot("slot_evidence", "EVIDENCE", "Three customers requested access."),
        slot("slot_risk", "RISK_UNKNOWN", "The delivery date is not confirmed."),
    ]

    output = RendererService().render("executive_summary", slots)

    assert output.output_type == "executive_summary"
    assert output.sections
    assert all(section.source_slot_ids for section in output.sections)
    assert all(section.source_segment_ids for section in output.sections)
    assert all(len(section.source_slot_ids) == len(section.source_segment_ids) for section in output.sections)


def test_renderer_rejects_sections_without_slot_provenance() -> None:
    with pytest.raises(UnsupportedClaimError, match="source semantic slot"):
        RendererService().validate_sections([SimpleNamespace(text="Invented claim", source_slot_ids=[], source_segment_ids=[])], [])


def test_clean_version_excludes_marked_content_and_keeps_its_reason() -> None:
    retained = SimpleNamespace(id="slot_keep", source_segment_id="seg_keep", slot_type=SimpleNamespace(value="FACT"), normalized_text="Keep this fact.")
    removed = SimpleNamespace(id="slot_remove", source_segment_id="seg_remove", slot_type=SimpleNamespace(value="FACT"), normalized_text="Duplicate fact.")
    label = SimpleNamespace(segment_id="seg_remove", label=SimpleNamespace(value="REDUNDANT"), reason="Same meaning as seg_keep")

    output = RendererService().render("clean_version", [retained, removed], quality_labels=[label])

    assert "Keep this fact." in output.content
    assert "Duplicate fact." not in "\n".join(section.text for section in output.sections if section.heading != "Removed candidates")
    notes = next(section for section in output.sections if section.heading == "Removed candidates")
    assert "Same meaning as seg_keep" in notes.text
    assert notes.source_slot_ids == ["slot_remove"]
    assert notes.source_segment_ids == ["seg_remove"]


def test_renderer_applies_requested_audience_and_word_limit() -> None:
    slots = [slot("slot_fact", "FACT", "one two three four five six")]

    output = RendererService().render("executive_summary", slots, audience="CEO", max_words=3)

    assert output.sections[0].heading.startswith("CEO:")
    assert len(output.sections[0].text.split()) == 3
