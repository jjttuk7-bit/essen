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


def _collapse(text: str) -> str:
    return " ".join(text.split())


def keep_verbatim_slots(analysis: ValidatedAnalysis, segment_texts: dict[str, str]) -> ValidatedAnalysis:
    """Drop anything the source does not actually say, and requote what it does.

    The product returns the source document's core, so a slot survives only when its text
    occurs in its own source segment. Whitespace is collapsed on both sides because
    extracted text carries line breaks a model will not reproduce; the surviving slot then
    carries the source's wording rather than the model's rendering of it.
    """
    kept = []
    for slot in analysis.slots:
        source = segment_texts.get(slot.source_segment_id)
        if source is None:
            continue
        collapsed_source = _collapse(source)
        quoted = _collapse(slot.text)
        if quoted and quoted in collapsed_source:
            kept.append(slot.model_copy(update={"text": quoted}))
    return analysis.model_copy(update={"slots": kept})


def validate_analysis_source_context(analysis: ValidatedAnalysis, source_segment_ids: set[str]) -> ValidatedAnalysis:
    """Reject provider results that cite a segment absent from the analysis request."""
    invalid_ids = sorted({slot.source_segment_id for slot in analysis.slots if slot.source_segment_id not in source_segment_ids})
    if invalid_ids:
        raise ValueError(f"semantic slot source_segment_id is not present in the request: {', '.join(invalid_ids)}")
    return analysis
