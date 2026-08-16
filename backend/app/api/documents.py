import hashlib
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_session
from app.models.analysis import AnalysisRun, AnalysisStatus, Gap, QualityCategory, QualityLabel, Relation, RenderedOutput, SemanticSlot
from app.models.document import Document, Segment
from app.schemas.api import DiagnosisResponse, RenderRequest, RenderResponse, RenderedOutputResponse, SemanticMapResponse
from app.schemas.document import DocumentUploadResponse
from app.services.llm.factory import create_llm_adapter
from app.services.parser.base import ParseError
from app.services.parser.service import DocumentParserService
from app.services.semantic.service import SemanticExtractionService
from app.services.signal.service import DiagnosisService
from app.services.renderer.service import RendererService


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



def _output_sections(output: RenderedOutput) -> list[dict[str, object]]:
    grouped: dict[int, dict[str, object]] = {}
    for reference in output.provenance:
        index = int(reference.get("section_index", 0))
        section = grouped.setdefault(index, {"heading": reference["heading"], "text": reference["text"], "source_slot_ids": [], "source_segment_ids": []})
        section["source_slot_ids"].append(reference["source_slot_id"])
        section["source_segment_ids"].append(reference["source_segment_id"])
    return [grouped[index] for index in sorted(grouped)]


def _output_response(output: RenderedOutput) -> RenderedOutputResponse:
    return RenderedOutputResponse(id=output.id, output_type=output.output_type, content=output.content, sections=_output_sections(output), version=output.version, audience=output.audience, max_words=output.max_words, render_config_hash=output.render_config_hash)


@router.post("/{document_id}/render", response_model=RenderResponse, status_code=status.HTTP_201_CREATED)
def render_document(document_id: str, request: RenderRequest | None = None, session: Session = Depends(get_session)) -> RenderResponse:
    document, run = _completed_analysis(session, document_id)
    slots = list(session.scalars(select(SemanticSlot).where(SemanticSlot.analysis_run_id == run.id)))
    labels = list(session.scalars(select(QualityLabel).where(QualityLabel.analysis_run_id == run.id)))
    requested = request or RenderRequest()
    output_types = [requested.output_type] if requested.output_type else ["clean_version", "executive_summary", "action_decision_sheet"]
    outputs: list[RenderedOutput] = []
    renderer = RendererService()
    try:
        for output_type in output_types:
            config = {"audience": requested.audience, "max_words": requested.max_words, "output_type": output_type}
            config_hash = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            output = session.scalar(select(RenderedOutput).where(RenderedOutput.analysis_run_id == run.id, RenderedOutput.output_type == output_type, RenderedOutput.render_config_hash == config_hash))
            if output is None:
                rendered = renderer.render(output_type, slots, labels, requested.audience, requested.max_words)
                provenance = [{"section_index": i, "heading": section.heading, "text": section.text, "source_slot_id": slot_id, "source_segment_id": segment_id} for i, section in enumerate(rendered.sections) for slot_id, segment_id in zip(section.source_slot_ids, section.source_segment_ids, strict=True)]
                for _ in range(3):
                    version = (session.scalar(select(func.max(RenderedOutput.version)).where(RenderedOutput.analysis_run_id == run.id, RenderedOutput.output_type == output_type)) or 0) + 1
                    candidate = RenderedOutput(analysis_run_id=run.id, document_id=document.id, output_type=output_type, content=rendered.content, version=version, audience=requested.audience, max_words=requested.max_words, render_config_hash=config_hash, provenance=provenance)
                    try:
                        with session.begin_nested():
                            session.add(candidate)
                            session.flush()
                        output = candidate
                        break
                    except IntegrityError:
                        output = session.scalar(select(RenderedOutput).where(RenderedOutput.analysis_run_id == run.id, RenderedOutput.output_type == output_type, RenderedOutput.render_config_hash == config_hash))
                        if output is not None:
                            break
                if output is None:
                    raise RuntimeError("Could not allocate a unique output version")
            outputs.append(output)
        session.commit()
        for output in outputs:
            session.refresh(output)
    except Exception:
        session.rollback()
        raise
    return RenderResponse(document_id=document.id, analysis_run_id=run.id, outputs=[_output_response(output) for output in outputs])


@router.get("/{document_id}/outputs", response_model=RenderResponse)
def get_outputs(document_id: str, session: Session = Depends(get_session)) -> RenderResponse:
    document, run = _completed_analysis(session, document_id)
    outputs = list(session.scalars(select(RenderedOutput).where(RenderedOutput.document_id == document.id, RenderedOutput.analysis_run_id == run.id).order_by(RenderedOutput.output_type, RenderedOutput.version)))
    return RenderResponse(document_id=document.id, analysis_run_id=run.id, outputs=[_output_response(output) for output in outputs])
