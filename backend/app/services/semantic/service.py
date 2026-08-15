from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisRun, AnalysisStatus, Relation, SemanticSlot
from app.models.document import Document, DocumentPurpose
from app.schemas.llm import AnalysisRequest, SourceSegment
from app.schemas.semantic import validate_analysis_source_context
from app.services.llm.base import LLMAdapter
from app.services.semantic.relations import build_documented_relations


PROMPT_VERSION = "semantic_extraction_v1"
LOW_CONFIDENCE_THRESHOLD = 0.7


@dataclass(frozen=True)
class ExtractionResult:
    analysis_run_id: str
    purpose: str
    audience: str
    semantic_slots: list[SemanticSlot]
    relations: list[Relation]
    review_required_slot_ids: list[str]


class SemanticExtractionService:
    def __init__(self, *, adapter: LLMAdapter, prompt_version: str = PROMPT_VERSION) -> None:
        self.adapter = adapter
        self.prompt_version = prompt_version

    def analyze_document(self, session: Session, document_id: str) -> ExtractionResult:
        document = session.get(Document, document_id)
        if document is None:
            raise LookupError(f"Document {document_id} was not found")
        existing = session.scalar(
            select(AnalysisRun).where(
                AnalysisRun.document_id == document.id,
                AnalysisRun.run_type == "semantic_extraction",
                AnalysisRun.prompt_version == self.prompt_version,
                AnalysisRun.status == AnalysisStatus.COMPLETED,
            )
        )
        if existing is not None:
            return self._result_for_run(session, document, existing)

        purpose, audience = self._classify(document)
        request = AnalysisRequest(
            prompt_version=self.prompt_version,
            segments=[SourceSegment(id=segment.id, text=segment.text) for segment in document.segments],
        )
        analysis = validate_analysis_source_context(self.adapter.analyze(request), {segment.id for segment in request.segments})
        run = AnalysisRun(document_id=document.id, run_type="semantic_extraction", status=AnalysisStatus.PENDING,
                          llm_backed=True, prompt_version=self.prompt_version, raw_model_output=analysis.model_dump_json())
        document.purpose = purpose
        document.audience = audience
        session.add(run)
        session.flush()
        slots = [SemanticSlot(analysis_run_id=run.id, source_segment_id=slot.source_segment_id, slot_type=slot.slot,
                              normalized_text=slot.text, confidence=slot.confidence, importance=slot.importance)
                 for slot in analysis.slots]
        session.add_all(slots)
        session.flush()
        relations = build_documented_relations(slots)
        session.add_all(relations)
        run.status = AnalysisStatus.COMPLETED
        session.commit()
        return self._result(document, run, slots, relations)

    @staticmethod
    def _classify(document: Document) -> tuple[DocumentPurpose, str]:
        text = document.raw_text.lower()
        if any(term in text for term in ("action:", "todo", "deploy", "implement", "execute")):
            return DocumentPurpose.EXECUTE, "implementation team"
        if any(term in text for term in ("decision", "recommend", "option", "approve")):
            return DocumentPurpose.DECIDE, "decision makers"
        return DocumentPurpose.EXPLAIN, "general readers"

    def _result_for_run(self, session: Session, document: Document, run: AnalysisRun) -> ExtractionResult:
        slots = list(session.scalars(select(SemanticSlot).where(SemanticSlot.analysis_run_id == run.id)))
        relations = list(session.scalars(select(Relation).join(SemanticSlot, Relation.from_slot_id == SemanticSlot.id)
                                         .where(SemanticSlot.analysis_run_id == run.id)))
        return self._result(document, run, slots, relations)

    @staticmethod
    def _result(document: Document, run: AnalysisRun, slots: list[SemanticSlot], relations: list[Relation]) -> ExtractionResult:
        return ExtractionResult(analysis_run_id=run.id, purpose=document.purpose.value if document.purpose else DocumentPurpose.EXPLAIN.value,
                                audience=document.audience or "general readers", semantic_slots=slots, relations=relations,
                                review_required_slot_ids=[slot.id for slot in slots if slot.confidence < LOW_CONFIDENCE_THRESHOLD])

