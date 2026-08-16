from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.diagnosis import QualityMetrics


class ProvenanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_segment_id: str


class QualityLabelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segment_id: str
    label: str
    score: float
    reason: str
    provenance: ProvenanceResponse


class DiagnosisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    analysis_run_id: str
    signal_ratio: float
    redundancy_ratio: float
    generic_ratio: float
    evidence_coverage: float
    decision_completeness: float
    actionability_score: float
    document_signal_score: float
    score_components: QualityMetrics
    gaps: list[str]
    counts: dict[str, int]
    explanations: list[str]
    labels: list[QualityLabelResponse]


class SemanticSlotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    slot: str
    text: str
    confidence: float
    importance: float
    provenance: ProvenanceResponse


class RelationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    from_slot_id: str
    relation_type: str
    to_slot_id: str


class SemanticMapResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    analysis_run_id: str
    purpose: str
    audience: str
    slots: list[SemanticSlotResponse]
    relations: list[RelationResponse]

class RenderedSectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str
    text: str
    source_slot_ids: list[str]
    source_segment_ids: list[str]


class RenderedOutputResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    output_type: str
    content: str
    sections: list[RenderedSectionResponse]
    version: int
    audience: str | None
    max_words: int | None
    render_config_hash: str


class RenderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    analysis_run_id: str
    outputs: list[RenderedOutputResponse]

class RenderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output_type: Literal["clean_version", "executive_summary", "action_decision_sheet"] | None = None
    audience: str | None = None
    max_words: int | None = Field(default=None, ge=1)
