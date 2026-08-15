import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from app.core.database import create_database_engine
from app.models.analysis import AnalysisRun, Gap, QualityLabel, RenderedOutput, SemanticSlot
from app.models.base import Base
from app.models.document import Document, Segment


def test_document_keeps_ordered_source_segments() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        document = Document(title="Plan", source_type="markdown", raw_text="# Plan")
        document.segments = [
            Segment(order_index=1, text="Second paragraph.", token_count=2),
            Segment(order_index=0, text="First paragraph.", token_count=2),
        ]
        session.add(document)
        session.commit()
        document_id = document.id

    with Session(engine) as fresh_session:
        persisted = fresh_session.get(Document, document_id)
        assert persisted is not None
        assert [(segment.order_index, segment.text) for segment in persisted.segments] == [
            (0, "First paragraph."),
            (1, "Second paragraph."),
        ]


def test_database_engine_enforces_foreign_key_cascades() -> None:
    engine = create_database_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        document = Document(title="Plan", source_type="markdown", raw_text="# Plan")
        document.segments = [Segment(order_index=0, text="# Plan", token_count=2)]
        session.add(document)
        session.commit()
        session.execute(delete(Document).where(Document.id == document.id))
        session.commit()

        assert session.scalars(select(Segment)).all() == []


def test_audit_records_belong_to_a_specific_analysis_run() -> None:
    engine = create_database_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        document = Document(title="Plan", source_type="markdown", raw_text="# Plan")
        segment = Segment(id="seg_plan", order_index=0, text="# Plan", token_count=2)
        document.segments = [segment]
        analysis_run = AnalysisRun(run_type="semantic", prompt_version="v1", raw_model_output="{}")
        document.analysis_runs = [analysis_run]
        slot = SemanticSlot(
            analysis_run=analysis_run,
            source_segment=segment,
            slot_type="FACT",
            normalized_text="Plan",
            confidence=0.9,
            importance=0.8,
        )
        label = QualityLabel(analysis_run=analysis_run, segment=segment, label="CORE_SIGNAL", score=0.9, reason="fact")
        gap = Gap(analysis_run=analysis_run, document=document, gap_type="MISSING_EVIDENCE", severity="WARNING", description="none")
        output = RenderedOutput(
            analysis_run=analysis_run,
            document=document,
            output_type="executive_summary",
            content="Plan",
            provenance=[{"source_segment_id": segment.id}],
        )
        session.add_all([document, slot, label, gap, output])
        session.commit()
        run_id = analysis_run.id
        slot_id = slot.id
        label_id = label.id
        gap_id = gap.id
        output_id = output.id

    with Session(engine) as fresh_session:
        assert fresh_session.get(SemanticSlot, slot_id).analysis_run_id == run_id
        assert fresh_session.get(QualityLabel, label_id).analysis_run_id == run_id
        assert fresh_session.get(Gap, gap_id).analysis_run_id == run_id
        assert fresh_session.get(RenderedOutput, output_id).analysis_run_id == run_id


def test_rendered_output_requires_nonempty_source_provenance() -> None:
    with pytest.raises(ValueError, match="provenance"):
        RenderedOutput(document_id="doc", analysis_run_id="run", output_type="executive_summary", content="Plan", provenance=[])

    output = RenderedOutput(
        document_id="doc",
        analysis_run_id="run",
        output_type="executive_summary",
        content="Plan",
        provenance=[{"source_segment_id": "segment_123"}],
    )
    assert output.provenance == [{"source_segment_id": "segment_123"}]
@pytest.mark.parametrize("source_id", ["", None])
def test_rendered_output_rejects_blank_source_ids(source_id: str | None) -> None:
    with pytest.raises(ValueError, match="provenance"):
        RenderedOutput(
            document_id="doc",
            analysis_run_id="run",
            output_type="executive_summary",
            content="Plan",
            provenance=[{"source_segment_id": source_id}],
        )


def test_rendered_output_provenance_must_reference_its_document_and_analysis_run() -> None:
    engine = create_database_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        first = Document(title="First", source_type="markdown", raw_text="# First")
        first_segment = Segment(order_index=0, text="# First", token_count=2)
        first.segments = [first_segment]
        first_run = AnalysisRun(run_type="semantic", prompt_version="v1", raw_model_output="{}")
        first.analysis_runs = [first_run]
        second = Document(title="Second", source_type="markdown", raw_text="# Second")
        second_segment = Segment(order_index=0, text="# Second", token_count=2)
        second.segments = [second_segment]
        second_run = AnalysisRun(run_type="semantic", prompt_version="v1", raw_model_output="{}")
        second.analysis_runs = [second_run]
        second_slot = SemanticSlot(
            analysis_run=second_run,
            source_segment=second_segment,
            slot_type="FACT",
            normalized_text="Second",
            confidence=0.9,
            importance=0.9,
        )
        session.add_all([first, second, second_slot])
        session.commit()
        first_document_id, first_run_id, first_segment_id = first.id, first_run.id, first_segment.id
        second_segment_id, second_slot_id = second_segment.id, second_slot.id

    valid = RenderedOutput(
        document_id=first_document_id,
        analysis_run_id=first_run_id,
        output_type="executive_summary",
        content="First",
        provenance=[{"source_segment_id": first_segment_id}],
    )
    with Session(engine) as session:
        session.add(valid)
        session.commit()

    invalid_references = [
        [{"source_segment_id": "unknown"}],
        [{"source_segment_id": second_segment_id}],
        [{"source_slot_id": second_slot_id}],
    ]
    for provenance in invalid_references:
        with Session(engine) as session:
            session.add(
                RenderedOutput(
                    document_id=first_document_id,
                    analysis_run_id=first_run_id,
                    output_type="executive_summary",
                    content="First",
                    provenance=provenance,
                )
            )
            with pytest.raises(ValueError, match="provenance"):
                session.commit()
