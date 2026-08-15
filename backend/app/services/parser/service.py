from pathlib import Path

from app.services.parser.base import ParsedDocument, ParseError, SourceParser
from app.services.parser.markdown import MarkdownParser
from app.services.parser.pdf import PdfParser
from app.services.parser.text import TextParser


class DocumentParserService:
    parsers: dict[str, SourceParser] = {
        ".txt": TextParser(),
        ".md": MarkdownParser(),
        ".markdown": MarkdownParser(),
        ".pdf": PdfParser(),
    }

    def parse(self, *, filename: str, content: bytes) -> ParsedDocument:
        parser = self.parsers.get(Path(filename).suffix.lower())
        if parser is None:
            raise ParseError("Unsupported file type. Upload TXT, Markdown, or PDF.")
        return parser.parse(content)
