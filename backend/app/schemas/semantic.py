from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.analysis import SlotType


class SemanticSlotPayload(BaseModel):
    """A source-linked semantic item returned by an LLM provider."""

    model_config = ConfigDict(extra="forbid")

    slot: SlotType
    text: Annotated[str, Field(min_length=1)]
    source_segment_id: Annotated[str, Field(min_length=1)]
    source_span: tuple[int, int] | None = None
    confidence: Annotated[float, Field(ge=0, le=1)]
    importance: Annotated[float, Field(ge=0, le=1)]
    evidence_links: list[str] = Field(default_factory=list)

    @field_validator("text", "source_segment_id")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class ValidatedAnalysis(BaseModel):
    """Validated provider result; only this type may be persisted downstream."""

    model_config = ConfigDict(extra="forbid")

    slots: list[SemanticSlotPayload] = Field(default_factory=list)


def validate_analysis_source_context(analysis: ValidatedAnalysis, source_segment_ids: set[str]) -> ValidatedAnalysis:
    """Reject provider results that cite a segment absent from the analysis request."""
    invalid_ids = sorted({slot.source_segment_id for slot in analysis.slots if slot.source_segment_id not in source_segment_ids})
    if invalid_ids:
        raise ValueError(f"semantic slot source_segment_id is not present in the request: {', '.join(invalid_ids)}")
    return analysis
