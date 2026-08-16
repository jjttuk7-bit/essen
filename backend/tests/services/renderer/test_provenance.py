from types import SimpleNamespace

import pytest

from app.services.renderer.service import RendererService, UnsupportedClaimError


def slot(slot_id: str, slot_type: str, text: str, importance: float = 0.8) -> SimpleNamespace:
    """Every extracted slot carries an importance; selection weighs it against the rules."""
    return SimpleNamespace(id=slot_id, source_segment_id=f"seg_{slot_id}", slot_type=SimpleNamespace(value=slot_type), normalized_text=text, importance=importance)


def test_every_rendered_section_cites_existing_semantic_slots_and_segments() -> None:
    slots = [
        slot("slot_decision", "DECISION", "Launch the pilot."),
        slot("slot_evidence", "EVIDENCE", "Three customers requested access."),
        slot("slot_risk", "RISK_UNKNOWN", "The delivery date is not confirmed."),
    ]

    output = RendererService().render("clean_version", slots)

    assert output.output_type == "clean_version"
    assert output.sections
    assert all(section.source_slot_ids for section in output.sections)
    assert all(section.source_segment_ids for section in output.sections)
    assert all(len(section.source_slot_ids) == len(section.source_segment_ids) for section in output.sections)


def test_renderer_rejects_sections_without_slot_provenance() -> None:
    with pytest.raises(UnsupportedClaimError, match="source semantic slot"):
        RendererService().validate_sections([SimpleNamespace(text="Invented claim", source_slot_ids=[], source_segment_ids=[])], [])


def test_clean_version_excludes_marked_content_from_the_document() -> None:
    """Removal reasons belong to the rewrite rationale, not to the document itself."""
    retained = slot("keep", "FACT", "Keep this fact.")
    removed = slot("remove", "FACT", "Duplicate fact.")
    label = SimpleNamespace(segment_id="seg_remove", label=SimpleNamespace(value="REDUNDANT"), reason="Same meaning as seg_keep")

    output = RendererService().render("clean_version", [retained, removed], quality_labels=[label])

    assert "Keep this fact." in output.content
    assert "Duplicate fact." not in output.content
    assert "Same meaning as seg_keep" not in output.content
    assert all(section.heading != "Removed candidates" for section in output.sections)


def test_renderer_applies_the_requested_audience() -> None:
    slots = [slot("slot_fact", "FACT", "one two three four five six")]

    output = RendererService().render("clean_version", slots, audience="CEO", max_words=6)

    assert output.sections[0].heading.startswith("CEO:")
    assert output.sections[0].text == "one two three four five six"


def test_a_word_limit_drops_an_item_that_does_not_fit_rather_than_truncating_it() -> None:
    slots = [slot("slot_fact", "FACT", "one two three four five six")]

    output = RendererService().render("clean_version", slots, max_words=3)

    assert output.sections == []


def test_section_lines_align_one_to_one_with_their_source_ids() -> None:
    """The reader needs discrete items, and each line must stay traceable to its slot."""
    from app.services.renderer.base import make_section

    class FakeSlot:
        def __init__(self, id, text, segment_id):
            self.id = id
            self.normalized_text = text
            self.source_segment_id = segment_id

    section = make_section("Decision", [
        FakeSlot("slot-1", "Launch the pilot in Q3.", "segment-1"),
        FakeSlot("slot-2", "Kim owns delivery.", "segment-2"),
    ])

    lines = section.text.split("\n")
    assert lines == ["Launch the pilot in Q3.", "Kim owns delivery."]
    assert len(lines) == len(section.source_slot_ids) == len(section.source_segment_ids)


def test_a_multi_line_slot_stays_on_one_line_so_alignment_holds() -> None:
    from app.services.renderer.base import make_section

    class FakeSlot:
        id = "slot-1"
        normalized_text = "First half.\nSecond half."
        source_segment_id = "segment-1"

    section = make_section("Decision", [FakeSlot()])

    assert section.text.split("\n") == ["First half. Second half."]
