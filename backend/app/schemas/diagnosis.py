from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class QualityMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    signal_ratio: float = Field(ge=0, le=1)
    redundancy_ratio: float = Field(ge=0, le=1)
    generic_ratio: float = Field(ge=0, le=1)
    evidence_coverage: float = Field(ge=0, le=1)
    decision_completeness: float = Field(ge=0, le=1)
    actionability_score: float = Field(ge=0, le=1)
    document_signal_score: float = Field(ge=0, le=1)


class Diagnosis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analysis_run_id: str
    metrics: QualityMetrics
    gaps: list[str]
    explanations: list[str]
