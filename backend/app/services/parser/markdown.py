from app.models.document import SourceType
from app.services.parser.base import ParsedDocument
from app.services.parser.text import TextParser


class MarkdownParser(TextParser):
    source_type = SourceType.MARKDOWN

    def parse(self, content: bytes) -> ParsedDocument:
        parsed = super().parse(content)
        return ParsedDocument(self.source_type, parsed.raw_text, parsed.segments)
