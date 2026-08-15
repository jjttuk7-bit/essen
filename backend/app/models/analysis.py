from __future__ import annotations

from enum import Enum
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, Enum as SqlEnum, event
from sqlalchemy import Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship, validates

from app.models.base import IdentifiedRecord
from app.models.document import Document, Segment


class SlotType(str, Enum):
    PURPOSE = "PURPOSE"; AUDIENCE = "AUDIENCE"; CONTEXT = "CONTEXT"; PROBLEM = "PROBLEM"; FACT = "FACT"
    EVIDENCE = "EVIDENCE"; INTERPRETATION = "INTERPRETATION"; DECISION = "DECISION"; ACTION = "ACTION"; RISK_UNKNOWN = "RISK_UNKNOWN"
    CLAIM = "CLAIM"; OPTION = "OPTION"; TRADE_OFF = "TRADE_OFF"; RECOMMENDATION = "RECOMMENDATION"; OWNER = "OWNER"
    DEADLINE = "DEADLINE"; PRIORITY = "PRIORITY"; SUCCESS_CRITERIA = "SUCCESS_CRITERIA"; SOURCE = "SOURCE"; CONFIDENCE = "CONFIDENCE"


class QualityCategory(str, Enum):
    CORE_SIGNAL = "CORE_SIGNAL"; SUPPORTING_SIGNAL = "SUPPORTING_SIGNAL"; CONTEXT = "CONTEXT"; REDUNDANT = "REDUNDANT"
    GENERIC = "GENERIC"; RHETORICAL = "RHETORICAL"; UNSUPPORTED = "UNSUPPORTED"; OFF_PURPOSE = "OFF_PURPOSE"


class Severity(str, Enum):
    INFO = "INFO"; WARNING = "WARNING"; ERROR = "ERROR"


class AnalysisStatus(str, Enum):
    PENDING = "PENDING"; COMPLETED = "COMPLETED"; FAILED = "FAILED"


def enum_values(values: type[Enum]) -> list[str]:
    return [value.value for value in values]


class SemanticSlot(IdentifiedRecord):
    __tablename__ = "semantic_slots"

    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    source_segment_id: Mapped[str] = mapped_column(ForeignKey("segments.id", ondelete="CASCADE"), nullable=False, index=True)
    slot_type: Mapped[SlotType] = mapped_column(SqlEnum(SlotType, values_callable=enum_values))
    normalized_text: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    importance: Mapped[float] = mapped_column(Float)

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="semantic_slots")
    source_segment: Mapped[Segment] = relationship(back_populates="slots")
    outgoing_relations: Mapped[list[Relation]] = relationship(back_populates="from_slot", foreign_keys="Relation.from_slot_id", cascade="all, delete-orphan")
    incoming_relations: Mapped[list[Relation]] = relationship(back_populates="to_slot", foreign_keys="Relation.to_slot_id", cascade="all, delete-orphan")


class Relation(IdentifiedRecord):
    __tablename__ = "relations"

    from_slot_id: Mapped[str] = mapped_column(ForeignKey("semantic_slots.id", ondelete="CASCADE"), index=True)
    relation_type: Mapped[str] = mapped_column(String(64))
    to_slot_id: Mapped[str] = mapped_column(ForeignKey("semantic_slots.id", ondelete="CASCADE"), index=True)

    from_slot: Mapped[SemanticSlot] = relationship(back_populates="outgoing_relations", foreign_keys=[from_slot_id])
    to_slot: Mapped[SemanticSlot] = relationship(back_populates="incoming_relations", foreign_keys=[to_slot_id])


class QualityLabel(IdentifiedRecord):
    __tablename__ = "quality_labels"

    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_id: Mapped[str] = mapped_column(ForeignKey("segments.id", ondelete="CASCADE"), index=True)
    label: Mapped[QualityCategory] = mapped_column(SqlEnum(QualityCategory, values_callable=enum_values))
    score: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text)

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="quality_labels")
    segment: Mapped[Segment] = relationship(back_populates="quality_labels")


class Gap(IdentifiedRecord):
    __tablename__ = "gaps"

    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    gap_type: Mapped[str] = mapped_column(String(64))
    severity: Mapped[Severity] = mapped_column(SqlEnum(Severity, values_callable=enum_values))
    description: Mapped[str] = mapped_column(Text)

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="gaps")
    document: Mapped[Document] = relationship(back_populates="gaps")


class RenderedOutput(IdentifiedRecord):
    __tablename__ = "rendered_outputs"
    __table_args__ = (CheckConstraint("provenance IS NOT NULL", name="ck_outputs_provenance_required"),)

    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    output_type: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(default=1)
    provenance: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="rendered_outputs")
    document: Mapped[Document] = relationship(back_populates="outputs")

    @validates("provenance")
    def validate_provenance(self, _: str, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Source provenance entries must cite a source segment or semantic slot ID."""
        if not value:
            raise ValueError("provenance must include source_segment_id or source_slot_id")
        for reference in value:
            if not isinstance(reference, dict):
                raise ValueError("provenance must include source_segment_id or source_slot_id")
            source_ids = [reference[key] for key in ("source_segment_id", "source_slot_id") if key in reference]
            if not source_ids or any(not isinstance(source_id, str) or not source_id.strip() for source_id in source_ids):
                raise ValueError("provenance must include non-empty source_segment_id or source_slot_id")
        return value


class AnalysisRun(IdentifiedRecord):
    __tablename__ = "analysis_runs"

    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    run_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[AnalysisStatus] = mapped_column(SqlEnum(AnalysisStatus, values_callable=enum_values), default=AnalysisStatus.PENDING)
    llm_backed: Mapped[bool] = mapped_column(Boolean, default=True)
    prompt_version: Mapped[str] = mapped_column(String(128), nullable=False)
    raw_model_output: Mapped[str] = mapped_column(Text, nullable=False)

    document: Mapped[Document] = relationship(back_populates="analysis_runs")
    semantic_slots: Mapped[list[SemanticSlot]] = relationship(back_populates="analysis_run", cascade="all, delete-orphan")
    quality_labels: Mapped[list[QualityLabel]] = relationship(back_populates="analysis_run", cascade="all, delete-orphan")
    gaps: Mapped[list[Gap]] = relationship(back_populates="analysis_run", cascade="all, delete-orphan")
    rendered_outputs: Mapped[list[RenderedOutput]] = relationship(back_populates="analysis_run", cascade="all, delete-orphan")

def _pending_or_persisted(session: Session, model_type: type[Any], record_id: str) -> Any | None:
    return next(
        (record for record in session.new if isinstance(record, model_type) and record.id == record_id),
        None,
    ) or session.get(model_type, record_id)


def _same_record(left: Any | None, right: Any | None) -> bool:
    return left is right or (left is not None and right is not None and left.id == right.id)


@event.listens_for(Session, "before_flush")
def validate_rendered_output_provenance(session: Session, _: Any, __: Any) -> None:
    """Validate normal ORM writes against the output's persisted source context."""
    for output in (record for record in session.new.union(session.dirty) if isinstance(record, RenderedOutput)):
        run = output.analysis_run or _pending_or_persisted(session, AnalysisRun, output.analysis_run_id)
        document = output.document or _pending_or_persisted(session, Document, output.document_id)
        if run is None or document is None or not _same_record(run.document, document):
            raise ValueError("provenance output must belong to its analysis run document")
        for reference in output.provenance:
            segment_id = reference.get("source_segment_id")
            if segment_id:
                segment = _pending_or_persisted(session, Segment, segment_id)
                if segment is None or not _same_record(segment.document, document):
                    raise ValueError("provenance source segment must belong to the output document")
            slot_id = reference.get("source_slot_id")
            if slot_id:
                slot = _pending_or_persisted(session, SemanticSlot, slot_id)
                if slot is None or not _same_record(slot.analysis_run, run):
                    raise ValueError("provenance source slot must belong to the output analysis run")
                slot_segment = _pending_or_persisted(session, Segment, slot.source_segment_id)
                if slot_segment is None or not _same_record(slot_segment.document, document):
                    raise ValueError("provenance source slot must belong to the output document")