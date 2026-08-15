from pydantic import BaseModel

from app.models.document import SourceType


class DocumentUploadResponse(BaseModel):
    document_id: str
    source_type: SourceType
    segment_count: int
