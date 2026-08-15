from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models.document import Document, Segment
from app.schemas.document import DocumentUploadResponse
from app.services.parser.base import ParseError
from app.services.parser.service import DocumentParserService


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
