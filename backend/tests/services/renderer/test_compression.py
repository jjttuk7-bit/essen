"""The product exists to return a shorter document, so compression is a contract."""

from app.services.renderer.base import ITEM_BUDGETS, select_by_importance
from app.services.renderer.service import RendererService


class FakeSlot:
    def __init__(self, index: int, slot_type: str, importance: float) -> None:
        self.id = f"slot-{index}"
        self.slot_type = slot_type
        self.normalized_text = f"Statement {index}."
        self.source_segment_id = f"segment-{index}"
        self.importance = importance
        self.confidence = 0.9


def _slots(count: int, slot_type: str = "FACT") -> list[FakeSlot]:
    # Ranked but never zero: a slot the model gave no weight at all is a different case.
    return [FakeSlot(index, slot_type, importance=(index + 1) / count) for index in range(count)]


def _item_count(document) -> int:
    """Distinct source material: the opening lines repeat the body, so they count once."""
    return len({slot_id for section in document.sections for slot_id in section.source_slot_ids})


def test_select_by_importance_keeps_the_highest_scoring_items() -> None:
    selected = select_by_importance(_slots(10), limit=3)

    assert [slot.id for slot in selected] == ["slot-9", "slot-8", "slot-7"]


def test_select_by_importance_keeps_document_order_within_the_selection() -> None:
    """Ranking decides what survives; the reader still wants source order."""
    selected = select_by_importance(_slots(10), limit=3, preserve_order=True)

    assert [slot.id for slot in selected] == ["slot-7", "slot-8", "slot-9"]


def test_every_output_stays_inside_its_item_budget() -> None:
    slots = _slots(60)

    for output_type, budget in ITEM_BUDGETS.items():
        document = RendererService().render(output_type, slots)
        assert _item_count(document) <= budget, output_type


def test_a_long_document_is_cut_down_hard() -> None:
    document = RendererService().render("clean_version", _slots(60))

    assert _item_count(document) <= ITEM_BUDGETS["clean_version"]
    assert _item_count(document) < 60


def test_outputs_no_longer_dump_unmatched_slots_into_a_catch_all() -> None:
    """A catch-all section defeats compression: nothing is ever left out."""
    document = RendererService().render("clean_version", _slots(60, slot_type="PURPOSE"))

    assert "Source-backed details" not in {section.heading for section in document.sections}


def test_a_short_document_is_returned_whole() -> None:
    document = RendererService().render("clean_version", _slots(3))

    assert _item_count(document) == 3


def test_compression_still_produces_something_for_low_signal_input() -> None:
    document = RendererService().render("clean_version", _slots(5, slot_type="CONTEXT"))

    assert document.sections


def test_a_word_limit_drops_whole_items_and_keeps_ids_aligned() -> None:
    """Truncating mid-item would collapse the line structure and desync source ids."""
    document = RendererService().render("clean_version", _slots(10), max_words=5)

    for section in document.sections:
        lines = section.text.split("\n")
        assert len(lines) == len(section.source_slot_ids) == len(section.source_segment_ids)
        assert all(line.endswith(".") for line in lines)


def test_a_word_limit_still_bounds_the_output() -> None:
    document = RendererService().render("clean_version", _slots(30), max_words=6)

    assert sum(len(section.text.split()) for section in document.sections) <= 6


class TestKeyPoints:
    """The reader should learn what the document says before reading the document."""

    def test_the_document_opens_with_a_three_line_core(self) -> None:
        document = RendererService().render("clean_version", _slots(20))

        assert document.sections[0].heading == "핵심 3줄"
        assert len(document.sections[0].text.split("\n")) == 3

    def test_the_core_lines_are_the_strongest_material(self) -> None:
        slots = _slots(20)
        document = RendererService().render("clean_version", slots)

        opening = set(document.sections[0].source_slot_ids)
        assert opening == {slot.id for slot in slots[-3:]}

    def test_the_core_keeps_source_order(self) -> None:
        document = RendererService().render("clean_version", _slots(20))

        assert document.sections[0].source_slot_ids == sorted(document.sections[0].source_slot_ids, key=lambda slot_id: int(slot_id.split("-")[1]))

    def test_a_short_document_opens_with_what_it_has(self) -> None:
        document = RendererService().render("clean_version", _slots(2))

        assert document.sections[0].heading == "핵심 2줄"

    def test_the_core_is_quoted_from_the_document_not_written_anew(self) -> None:
        slots = _slots(20)
        document = RendererService().render("clean_version", slots)

        texts = {slot.normalized_text for slot in slots}
        assert all(line in texts for line in document.sections[0].text.split("\n"))

    def test_an_empty_document_has_no_core_section(self) -> None:
        assert RendererService().render("clean_version", []).sections == []
