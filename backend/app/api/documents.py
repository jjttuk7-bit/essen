from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models.document import Document, Segment
from app.schemas.document import DocumentUploadResponse
from app.services.parser.base import ParseError
from app.services.parser.service import DocumentParserService
from app.core.config import get_settings
from app.services.llm.factory import create_llm_adapter
from app.services.semantic.service import SemanticExtractionService


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
