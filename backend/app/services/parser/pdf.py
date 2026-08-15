from io import BytesIO

from pypdf import PdfReader

from app.models.document import SourceType
from app.services.parser.base import ParsedDocument, ParseError, ParsedSegment, normalize_text, segments_for_text


class PdfParser:
    source_type = SourceType.PDF

    def parse(self, content: bytes) -> ParsedDocument:
        try:
            reader = PdfReader(BytesIO(content))
            pages = [normalize_text(page.extract_text() or "") for page in reader.pages]
        except Exception as error:
            raise ParseError("PDF has no extractable text or could not be read") from error

        segments: list[ParsedSegment] = []
        raw_pages: list[str] = []
        paragraph = 1
        for page_number, page_text in enumerate(pages, start=1):
            if not page_text:
                continue
            raw_pages.append(page_text)
            page_segments = segments_for_text(page_text, page=page_number, start_paragraph=paragraph)
            for segment in page_segments:
                segments.append(ParsedSegment(len(segments), segment.text, segment.page, segment.paragraph))
            paragraph += len(page_segments)
        if not segments:
            raise ParseError("PDF contains no extractable text; OCR is required")
        return ParsedDocument(self.source_type, "\n\n".join(raw_pages), segments)
