from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_session
from app.models.analysis import AnalysisRun, AnalysisStatus, Gap, QualityCategory, QualityLabel, Relation, SemanticSlot
from app.models.document import Document, Segment
from app.schemas.api import DiagnosisResponse, SemanticMapResponse
from app.schemas.document import DocumentUploadResponse
from app.services.llm.factory import create_llm_adapter
from app.services.parser.base import ParseError
from app.services.parser.service import DocumentParserService
from app.services.semantic.service import SemanticExtractionService
from app.services.signal.service import DiagnosisService


router = APIRouter(prefix="/documents", tags=["documents"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
UPLOAD_READ_CHUNK_BYTES = 64 * 1024


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile, session: Session = Depends(get_session)) -> DocumentUploadResponse:
    filename = file.filename or ""
    content_parts: list[bytes] = []
    total_bytes = 0
    while True:
        read_size = min(UPLOAD_READ_CHUNK_BYTES, MAX_UPLOAD_BYTES + 1 - total_bytes)
        chunk = await file.read(read_size)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Upload exceeds the 10 MB size limit")
        content_parts.append(chunk)
    content = b"".join(content_parts)
    if not filename:
        raise HTTPException(status_code=422, detail="A filename is required")
    try:
        parsed = DocumentParserService().parse(filename=filename, content=content)
    except ParseError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    document = Document(title=Path(filename).stem, source_type=parsed.source_type, raw_text=parsed.raw_text)
    document.segments = [
        Segment(order_index=segment.order_index, text=segment.text, page=segment.page,
                paragraph=segment.paragraph, token_count=segment.token_count)
        for segment in parsed.segments
    ]
    try:
        session.add(document)
        session.commit()
        session.refresh(document)
    except Exception:
        session.rollback()
        raise
    return DocumentUploadResponse(document_id=document.id, source_type=document.source_type,
                                  segment_count=len(document.segments))


@router.post("/{document_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
def analyze_document(document_id: str, session: Session = Depends(get_session)) -> dict[str, object]:
    service = SemanticExtractionService(adapter=create_llm_adapter(get_settings()))
    try:
        result = service.analyze_document(session, document_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail="Document not found") from error
    except Exception:
        session.rollback()
        raise
    return {
        "analysis_run_id": result.analysis_run_id,
        "document_id": document_id,
        "purpose": result.purpose,
        "audience": result.audience,
        "semantic_slots": [
            {
                "id": slot.id,
                "slot": slot.slot_type.value,
                "text": slot.normalized_text,
                "source_segment_id": slot.source_segment_id,
                "confidence": slot.confidence,
                "importance": slot.importance,
            }
            for slot in result.semantic_slots
        ],
        "relations": [
            {"from_slot_id": relation.from_slot_id, "relation_type": relation.relation_type, "to_slot_id": relation.to_slot_id}
            for relation in result.relations
        ],
        "review_required_slot_ids": result.review_required_slot_ids,
    }


def _completed_analysis(session: Session, document_id: str) -> tuple[Document, AnalysisRun]:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    run = session.scalar(
        select(AnalysisRun)
        .where(AnalysisRun.document_id == document_id, AnalysisRun.status == AnalysisStatus.COMPLETED)
        .order_by(AnalysisRun.created_at.desc())
    )
    if run is None:
        raise HTTPException(status_code=409, detail="Document has no completed analysis")
    return document, run


@router.get("/{document_id}/diagnosis", response_model=DiagnosisResponse)
def get_diagnosis(document_id: str, session: Session = Depends(get_session)) -> DiagnosisResponse:
    document, run = _completed_analysis(session, document_id)
    diagnosis = DiagnosisService().diagnose_document(session, document_id)
    labels = list(session.scalars(
        select(QualityLabel).where(QualityLabel.analysis_run_id == run.id).order_by(QualityLabel.created_at, QualityLabel.id)
    ))
    gaps = list(session.scalars(select(Gap).where(Gap.analysis_run_id == run.id).order_by(Gap.created_at, Gap.id)))
    slots = list(session.scalars(select(SemanticSlot).where(SemanticSlot.analysis_run_id == run.id)))
    relations = list(session.scalars(
        select(Relation).join(SemanticSlot, Relation.from_slot_id == SemanticSlot.id)
        .where(SemanticSlot.analysis_run_id == run.id)
    ))
    metrics = diagnosis.metrics
    return DiagnosisResponse(
        document_id=document.id,
        analysis_run_id=run.id,
        signal_ratio=metrics.signal_ratio,
        redundancy_ratio=metrics.redundancy_ratio,
        generic_ratio=metrics.generic_ratio,
        evidence_coverage=metrics.evidence_coverage,
        decision_completeness=metrics.decision_completeness,
        actionability_score=metrics.actionability_score,
        document_signal_score=metrics.document_signal_score,
        score_components=metrics,
        gaps=[gap.gap_type for gap in gaps],
        counts={
            "segments": len(document.segments),
            "semantic_slots": len(slots),
            "relations": len(relations),
            "gaps": len(gaps),
            **{category.value.lower(): sum(label.label == category for label in labels) for category in QualityCategory},
        },
        explanations=diagnosis.explanations,
        labels=[
            {
                "segment_id": label.segment_id,
                "label": label.label.value,
                "score": label.score,
                "reason": label.reason,
                "provenance": {"source_segment_id": label.segment_id},
            }
            for label in labels
        ],
    )


@router.get("/{document_id}/semantic-map", response_model=SemanticMapResponse)
def get_semantic_map(document_id: str, session: Session = Depends(get_session)) -> SemanticMapResponse:
    document, run = _completed_analysis(session, document_id)
    slots = list(session.scalars(
        select(SemanticSlot).where(SemanticSlot.analysis_run_id == run.id).order_by(SemanticSlot.created_at, SemanticSlot.id)
    ))
    relations = list(session.scalars(
        select(Relation).join(SemanticSlot, Relation.from_slot_id == SemanticSlot.id)
        .where(SemanticSlot.analysis_run_id == run.id).order_by(Relation.created_at, Relation.id)
    ))
    return SemanticMapResponse(
        document_id=document.id,
        analysis_run_id=run.id,
        purpose=document.purpose.value if document.purpose else "EXPLAIN",
        audience=document.audience or "general readers",
        slots=[
            {
                "id": slot.id,
                "slot": slot.slot_type.value,
                "text": slot.normalized_text,
                "confidence": slot.confidence,
                "importance": slot.importance,
                "provenance": {"source_segment_id": slot.source_segment_id},
            }
            for slot in slots
        ],
        relations=[
            {
                "id": relation.id,
                "from_slot_id": relation.from_slot_id,
                "relation_type": relation.relation_type,
                "to_slot_id": relation.to_slot_id,
            }
            for relation in relations
        ],
    )
