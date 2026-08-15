from __future__ import annotations

from enum import Enum

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import IdentifiedRecord


class SourceType(str, Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    PDF = "pdf"


class DocumentPurpose(str, Enum):
    INFORM = "INFORM"
    EXPLAIN = "EXPLAIN"
    DECIDE = "DECIDE"
    PERSUADE = "PERSUADE"
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    RECORD = "RECORD"


class Document(IdentifiedRecord):
    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(500))
    source_type: Mapped[SourceType] = mapped_column(
        SqlEnum(SourceType, values_callable=lambda values: [value.value for value in values])
    )
    raw_text: Mapped[str] = mapped_column(Text)
    purpose: Mapped[DocumentPurpose | None] = mapped_column(
        SqlEnum(DocumentPurpose, values_callable=lambda values: [value.value for value in values]), nullable=True
    )
    audience: Mapped[str | None] = mapped_column(String(255), nullable=True)

    segments: Mapped[list[Segment]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="Segment.order_index"
    )
    gaps: Mapped[list[Gap]] = relationship(back_populates="document", cascade="all, delete-orphan")
    outputs: Mapped[list[RenderedOutput]] = relationship(back_populates="document", cascade="all, delete-orphan")
    analysis_runs: Mapped[list[AnalysisRun]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Segment(IdentifiedRecord):
    __tablename__ = "segments"
    __table_args__ = (UniqueConstraint("document_id", "order_index", name="uq_segments_document_order"),)

    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    order_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paragraph: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_count: Mapped[int] = mapped_column(Integer)

    document: Mapped[Document] = relationship(back_populates="segments")
    slots: Mapped[list[SemanticSlot]] = relationship(back_populates="source_segment", cascade="all, delete-orphan")
    quality_labels: Mapped[list[QualityLabel]] = relationship(
        back_populates="segment", cascade="all, delete-orphan"
    )

# Register the analysis models before SQLAlchemy configures Document relationships.
import app.models.analysis  # noqa: E402, F401
