from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models.analysis import AnalysisRun, Relation, SemanticSlot, SlotType
from app.models.base import Base
from app.models.document import Document, SourceType, Segment
from app.schemas.semantic import SemanticSlotPayload, ValidatedAnalysis
from app.services.llm.base import LLMAdapter
from app.services.llm.rule_based import RuleBasedLLMAdapter
from app.services.semantic.relations import build_documented_relations
from app.services.semantic.service import SemanticExtractionService


def test_extraction_persists_source_linked_slots_relations_and_review_items() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        document = Document(title="Plan", source_type=SourceType.TEXT, raw_text="Action: deploy by Friday.")
        document.segments = [Segment(order_index=0, text=document.raw_text, page=None, paragraph=1, token_count=5)]
        session.add(document)
        session.commit()

        result = SemanticExtractionService(adapter=RuleBasedLLMAdapter()).analyze_document(session, document.id)

        assert result.purpose == "EXECUTE"
        assert result.audience == "implementation team"
        assert result.review_required_slot_ids
        assert session.scalars(select(AnalysisRun)).one().raw_model_output
        slots = session.scalars(select(SemanticSlot)).all()
        assert slots and {slot.source_segment_id for slot in slots} == {document.segments[0].id}
        assert session.scalars(select(Relation)).all() == []


def test_documented_relations_are_directional_and_never_cross_source_segments() -> None:
    slots = [
        SemanticSlot(id="fact", analysis_run_id="run", source_segment_id="a", slot_type=SlotType.FACT, normalized_text="fact", confidence=1, importance=1),
        SemanticSlot(id="evidence", analysis_run_id="run", source_segment_id="a", slot_type=SlotType.EVIDENCE, normalized_text="evidence", confidence=1, importance=1),
        SemanticSlot(id="decision", analysis_run_id="run", source_segment_id="b", slot_type=SlotType.DECISION, normalized_text="decision", confidence=1, importance=1),
        SemanticSlot(id="action", analysis_run_id="run", source_segment_id="b", slot_type=SlotType.ACTION, normalized_text="action", confidence=1, importance=1),
        SemanticSlot(id="owner", analysis_run_id="run", source_segment_id="b", slot_type=SlotType.OWNER, normalized_text="owner", confidence=1, importance=1),
        SemanticSlot(id="unrelated-fact", analysis_run_id="run", source_segment_id="c", slot_type=SlotType.FACT, normalized_text="unrelated", confidence=1, importance=1),
        SemanticSlot(id="unrelated-action", analysis_run_id="run", source_segment_id="d", slot_type=SlotType.ACTION, normalized_text="unrelated", confidence=1, importance=1),
    ]

    relations = build_documented_relations(slots)

    assert {(relation.from_slot_id, relation.relation_type, relation.to_slot_id) for relation in relations} == {
        ("fact", "supported_by", "evidence"),
        ("decision", "triggers", "action"),
        ("action", "owned_by", "owner"),
    }


class InvalidSourceAdapter(LLMAdapter):
    def analyze(self, request) -> ValidatedAnalysis:
        return ValidatedAnalysis(slots=[SemanticSlotPayload(slot=SlotType.FACT, text="invented", source_segment_id="missing", confidence=1, importance=1)])


def test_extraction_rejects_adapter_slots_outside_document_source_context() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        document = Document(title="Brief", source_type=SourceType.TEXT, raw_text="Known source.")
        document.segments = [Segment(order_index=0, text=document.raw_text, page=None, paragraph=1, token_count=2)]
        session.add(document)
        session.commit()

        try:
            SemanticExtractionService(adapter=InvalidSourceAdapter()).analyze_document(session, document.id)
        except ValueError as error:
            assert "source_segment_id" in str(error)
        else:
            raise AssertionError("unknown adapter source must be rejected before persistence")
        assert not session.scalars(select(AnalysisRun)).all()


def test_extraction_is_idempotent_for_the_same_document_and_prompt_version() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        document = Document(title="Brief", source_type=SourceType.TEXT, raw_text="A fact.")
        document.segments = [Segment(order_index=0, text="A fact.", page=None, paragraph=1, token_count=2)]
        session.add(document)
        session.commit()
        service = SemanticExtractionService(adapter=RuleBasedLLMAdapter())

        first = service.analyze_document(session, document.id)
        second = service.analyze_document(session, document.id)

        assert first.analysis_run_id == second.analysis_run_id
        assert len(session.scalars(select(AnalysisRun)).all()) == 1


