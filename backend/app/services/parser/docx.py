"""Read a Word document without a third-party reader.

A .docx is a zip holding one XML part, and the text lives in a shallow structure: a body
of paragraphs and tables, each paragraph a sequence of runs that Word splits wherever
formatting changes. Rejoining runs and keeping table rows on their own lines is all the
rest of the pipeline needs — the shape rules then recognise a table as a table.
"""

from io import BytesIO
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from app.models.document import SourceType
from app.services.parser.base import ParsedDocument, ParseError, ParsedSegment, normalize_text

WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
DOCUMENT_PART = "word/document.xml"


def _paragraph_text(paragraph: ElementTree.Element) -> str:
    parts: list[str] = []
    for node in paragraph.iter():
        if node.tag == f"{WORD}t":
            parts.append(node.text or "")
        elif node.tag == f"{WORD}tab":
            parts.append("\t")
        elif node.tag in (f"{WORD}br", f"{WORD}cr"):
            parts.append("\n")
    return "".join(parts).strip()


def _table_text(table: ElementTree.Element) -> str:
    """One line per row, cells tab-separated, so the table keeps its shape downstream."""
    rows = []
    for row in table.iter(f"{WORD}tr"):
        cells = [_paragraph_text(cell) for cell in row.iter(f"{WORD}tc")]
        if any(cells):
            rows.append("\t".join(cells))
    return "\n".join(rows)


class DocxParser:
    source_type = SourceType.DOCX

    def parse(self, content: bytes) -> ParsedDocument:
        try:
            with ZipFile(BytesIO(content)) as archive:
                document = archive.read(DOCUMENT_PART)
        except (BadZipFile, KeyError) as error:
            raise ParseError("Not a readable Word document") from error
        try:
            body = ElementTree.fromstring(document).find(f"{WORD}body")
        except ElementTree.ParseError as error:
            raise ParseError("Not a readable Word document") from error
        if body is None:
            raise ParseError("Not a readable Word document")

        blocks: list[str] = []
        for node in body:
            if node.tag == f"{WORD}p":
                blocks.append(_paragraph_text(node))
            elif node.tag == f"{WORD}tbl":
                blocks.append(_table_text(node))
        texts = [normalize_text(block) for block in blocks]

        segments = [
            ParsedSegment(order_index=index, text=text, page=None, paragraph=index + 1)
            for index, text in enumerate(text for text in texts if text)
        ]
        if not segments:
            raise ParseError("Word document contains no text")
        return ParsedDocument(self.source_type, "\n\n".join(segment.text for segment in segments), segments)
