"""The condensed document must be built from the source's own wording.

The product's promise is the source document's core, not a new document about it. A model
that writes its own sentences produces commentary ("이 문서는 ~를 제시한다") and can state
things the source never said, so generated wording is rejected rather than trusted.
"""

import pytest

from app.schemas.semantic import ValidatedAnalysis, keep_verbatim_slots

SEGMENT = "새 데이터를 받으면 파일을 열기 전에, 또는 연 직후 10분 안에 아래 항목부터 확인한다. 이 단계를 건너뛰면 나중에 훨씬 큰 시간을 들여 되돌아와야 한다."


def _analysis(*texts: str) -> ValidatedAnalysis:
    return ValidatedAnalysis.model_validate({
        "slots": [
            {"slot": "ACTION", "text": text, "source_segment_id": "segment-1", "confidence": 0.9, "importance": 0.9}
            for text in texts
        ]
    })


def test_a_quoted_sentence_is_kept() -> None:
    analysis = keep_verbatim_slots(_analysis("이 단계를 건너뛰면 나중에 훨씬 큰 시간을 들여 되돌아와야 한다."), {"segment-1": SEGMENT})

    assert len(analysis.slots) == 1


def test_a_paraphrase_is_dropped() -> None:
    analysis = keep_verbatim_slots(_analysis("이 문서는 첫 10분 체크리스트를 제시한다."), {"segment-1": SEGMENT})

    assert analysis.slots == []


def test_whitespace_differences_do_not_reject_a_real_quote() -> None:
    """Extracted text carries line breaks the model will not reproduce exactly."""
    analysis = keep_verbatim_slots(_analysis("파일을 열기 전에,   또는 연\n직후 10분 안에"), {"segment-1": SEGMENT})

    assert len(analysis.slots) == 1


def test_the_kept_text_is_the_source_wording_not_the_model_wording() -> None:
    analysis = keep_verbatim_slots(_analysis("파일을 열기 전에,   또는 연\n직후 10분 안에"), {"segment-1": SEGMENT})

    assert analysis.slots[0].text == "파일을 열기 전에, 또는 연 직후 10분 안에"


def test_a_slot_citing_an_unknown_segment_is_dropped() -> None:
    analysis = keep_verbatim_slots(_analysis("이 단계를 건너뛰면"), {"segment-2": SEGMENT})

    assert analysis.slots == []


def test_mixed_results_keep_only_the_quotes() -> None:
    analysis = keep_verbatim_slots(
        _analysis("이 단계를 건너뛰면 나중에 훨씬 큰 시간을 들여 되돌아와야 한다.", "이 문서는 체크리스트를 제시한다."),
        {"segment-1": SEGMENT},
    )

    assert [slot.text for slot in analysis.slots] == ["이 단계를 건너뛰면 나중에 훨씬 큰 시간을 들여 되돌아와야 한다."]


@pytest.mark.parametrize("invented", ["", "   ", "완전히 없는 문장이다."])
def test_empty_or_invented_text_never_survives(invented: str) -> None:
    try:
        analysis = _analysis(invented)
    except ValueError:
        return
    assert keep_verbatim_slots(analysis, {"segment-1": SEGMENT}).slots == []
