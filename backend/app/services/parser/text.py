from app.models.document import SourceType
from app.services.parser.base import ParsedDocument, ParseError, normalize_text, segments_for_text


class TextParser:
    source_type = SourceType.TEXT

    def parse(self, content: bytes) -> ParsedDocument:
        try:
            text = normalize_text(content.decode("utf-8"))
        except UnicodeDecodeError as error:
            raise ParseError("Text uploads must use UTF-8 encoding") from error
        if not text:
            raise ParseError("Uploaded source contains no text")
        return ParsedDocument(self.source_type, text, segments_for_text(text))
