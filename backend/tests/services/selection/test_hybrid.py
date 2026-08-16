"""Combining the rule layer with the model's contextual judgement.

The rules decide what is even a candidate and supply the wording of the reason; the model
judges what matters given what the document is for. Neither alone is trusted, and no
source section is allowed to vanish silently.
"""

from types import SimpleNamespace

from app.services.selection.hybrid import Verdict, select_core


def _slot(index: int, text: str, importance: float, segment_id: str) -> SimpleNamespace:
    return SimpleNamespace(id=f"slot-{index}", normalized_text=text, source_segment_id=segment_id, importance=importance)


DIRECTIVE = "이 확인 없이 다음 단계로 넘어가지 않는다."
GENERALITY = "일반적으로 품질은 매우 중요하다."
NEUTRAL = "문서는 열세 개의 부로 이루어져 있다."


class _Outline:
    def __init__(self, mapping: dict[str, str]) -> None:
        self._mapping = mapping
        self.ordered_headings = list(dict.fromkeys(mapping.values()))

    def heading_for(self, segment_id: str) -> str | None:
        return self._mapping.get(segment_id)

    def position_of(self, segment_id: str) -> int:
        return list(self._mapping).index(segment_id) if segment_id in self._mapping else 99


def test_the_rules_and_the_model_agreeing_keeps_a_passage() -> None:
    kept = select_core([_slot(0, DIRECTIVE, 0.9, "segment-0")], segment_texts={"segment-0": DIRECTIVE}, outline=None, budget=10)

    assert kept[0].verdict is Verdict.AGREED_KEEP
    assert "실행 지시" in kept[0].reason


def test_both_scoring_a_passage_low_drops_it() -> None:
    kept = select_core([_slot(0, GENERALITY, 0.1, "segment-0")], segment_texts={"segment-0": GENERALITY}, outline=None, budget=10)

    assert kept == []


def test_a_passage_only_the_model_values_is_kept_and_marked() -> None:
    kept = select_core([_slot(0, NEUTRAL, 0.95, "segment-0")], segment_texts={"segment-0": NEUTRAL}, outline=None, budget=10)

    assert kept[0].verdict is Verdict.MODEL_ONLY
    assert "문맥상 중요" in kept[0].reason


def test_a_passage_only_the_rules_value_is_kept_and_marked() -> None:
    kept = select_core([_slot(0, DIRECTIVE, 0.05, "segment-0")], segment_texts={"segment-0": DIRECTIVE}, outline=None, budget=10)

    assert kept[0].verdict is Verdict.RULE_ONLY
    assert "실행 지시" in kept[0].reason


def test_the_budget_is_respected() -> None:
    slots = [_slot(index, DIRECTIVE, 0.9, f"segment-{index}") for index in range(20)]
    texts = {f"segment-{index}": DIRECTIVE for index in range(20)}

    kept = select_core(slots, segment_texts=texts, outline=None, budget=5)

    assert len(kept) == 5


def test_no_source_section_disappears_silently() -> None:
    """Whole sections vanishing makes the result a mutilation rather than a condensation."""
    slots = [_slot(index, DIRECTIVE if index < 8 else NEUTRAL, 0.9 if index < 8 else 0.2, f"segment-{index}") for index in range(10)]
    texts = {f"segment-{index}": slots[index].normalized_text for index in range(10)}
    outline = _Outline({f"segment-{index}": f"PART {index // 5 + 1}" for index in range(10)})

    kept = select_core(slots, segment_texts=texts, outline=outline, budget=6)

    assert {outline.heading_for(item.slot.source_segment_id) for item in kept} == {"PART 1", "PART 2"}
    assert len(kept) <= 6


def test_sections_keep_their_source_order() -> None:
    slots = [_slot(index, DIRECTIVE, 0.9, f"segment-{index}") for index in range(4)]
    texts = {f"segment-{index}": DIRECTIVE for index in range(4)}
    outline = _Outline({f"segment-{index}": f"PART {index + 1}" for index in range(4)})

    kept = select_core(slots, segment_texts=texts, outline=outline, budget=4)

    assert [item.slot.source_segment_id for item in kept] == ["segment-0", "segment-1", "segment-2", "segment-3"]


def test_a_stronger_passage_wins_the_place_inside_a_section() -> None:
    slots = [_slot(0, NEUTRAL, 0.3, "segment-0"), _slot(1, DIRECTIVE, 0.9, "segment-1")]
    texts = {"segment-0": NEUTRAL, "segment-1": DIRECTIVE}
    outline = _Outline({"segment-0": "PART 1", "segment-1": "PART 1"})

    kept = select_core(slots, segment_texts=texts, outline=outline, budget=1)

    assert kept[0].slot.id == "slot-1"


def test_every_kept_passage_explains_itself() -> None:
    slots = [_slot(index, DIRECTIVE, 0.9, f"segment-{index}") for index in range(3)]
    texts = {f"segment-{index}": DIRECTIVE for index in range(3)}

    assert all(item.reason for item in select_core(slots, segment_texts=texts, outline=None, budget=3))


def test_selection_is_reproducible() -> None:
    slots = [_slot(index, DIRECTIVE, 0.9, f"segment-{index}") for index in range(6)]
    texts = {f"segment-{index}": DIRECTIVE for index in range(6)}

    first = [item.slot.id for item in select_core(slots, segment_texts=texts, outline=None, budget=3)]
    second = [item.slot.id for item in select_core(slots, segment_texts=texts, outline=None, budget=3)]

    assert first == second


class TestFurnitureCannotBeVotedUp:
    """Form is a fact about the document; a model's enthusiasm does not change it."""

    # Shaped like the real thing: each row ends in an output column, not a sentence.
    TABLE = ("단계 이름 핵심 질문 산출물 1 문제정의 무엇을 알고 싶은가? 문제정의서 1장 2 데이터 이해 한 행은 무엇을 의미하는가? "
             "데이터 사전 3 품질진단 믿고 써도 되는가? 품질진단 리포트 4 탐색 어떤 모습인가? 기초 통계 5 원인/관계분석 왜인가? 관계도")

    def test_a_table_the_model_loves_still_ranks_below_prose(self) -> None:
        slots = [_slot(0, self.TABLE, 1.0, "segment-0"), _slot(1, DIRECTIVE, 0.6, "segment-1")]
        texts = {"segment-0": self.TABLE, "segment-1": DIRECTIVE}

        kept = select_core(slots, segment_texts=texts, outline=None, budget=2)

        assert [item.slot.id for item in sorted(kept, key=lambda item: -item.score)][0] == "slot-1"

    def test_a_table_is_still_kept_when_the_document_has_room(self) -> None:
        """Held below prose, not thrown out: the body still carries the source's tables."""
        slots = [_slot(0, self.TABLE, 1.0, "segment-0")]

        kept = select_core(slots, segment_texts={"segment-0": self.TABLE}, outline=None, budget=5)

        assert [item.slot.id for item in kept] == ["slot-0"]
