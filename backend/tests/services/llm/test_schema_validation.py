import pytest
from pydantic import ValidationError

from app.schemas.semantic import SemanticSlotPayload, ValidatedAnalysis


def test_schema_rejects_an_unknown_semantic_slot() -> None:
    with pytest.raises(ValidationError):
        SemanticSlotPayload.model_validate(
            {
                "slot": "INVENTED_SLOT",
                "text": "A source-backed statement.",
                "source_segment_id": "segment-1",
                "confidence": 0.8,
                "importance": 0.7,
            }
        )


def test_schema_rejects_a_blank_source_segment_id() -> None:
    with pytest.raises(ValidationError):
        SemanticSlotPayload.model_validate(
            {
                "slot": "FACT",
                "text": "A source-backed statement.",
                "source_segment_id": "  ",
                "confidence": 0.8,
                "importance": 0.7,
            }
        )


def test_validated_analysis_accepts_multiple_labels_for_one_segment() -> None:
    analysis = ValidatedAnalysis.model_validate(
        {
            "slots": [
                {"slot": "FACT", "text": "Deploy Friday.", "source_segment_id": "segment-1", "confidence": 0.8, "importance": 0.8},
                {"slot": "DEADLINE", "text": "Friday", "source_segment_id": "segment-1", "confidence": 0.9, "importance": 0.8},
            ]
        }
    )

    assert [slot.slot.value for slot in analysis.slots] == ["FACT", "DEADLINE"]
