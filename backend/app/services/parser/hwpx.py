"""Read an HWPX document, the format most Korean public-sector documents now use.

Like .docx it is a zip of XML, so no third-party reader is needed. Unlike .docx a table
is nested inside the paragraph that holds it, so paragraph text is collected while
stepping over table subtrees, and each table is then emitted as its own block with a row
per line — the shape rules downstream recognise a table by that shape.
"""

import re
from io import BytesIO
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from app.models.document import SourceType
from app.services.parser.base import ParsedDocument, ParseError, ParsedSegment, normalize_text

PARAGRAPH_NS = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
PARAGRAPH = f"{PARAGRAPH_NS}p"
TEXT = f"{PARAGRAPH_NS}t"
TABLE = f"{PARAGRAPH_NS}tbl"
ROW = f"{PARAGRAPH_NS}tr"
CELL = f"{PARAGRAPH_NS}tc"
SECTION = re.compile(r"^Contents/section(\d+)\.xml$")


def _collect_text(node: ElementTree.Element, parts: list[str], skip: tuple[str, ...] = ()) -> None:
    for child in node:
        if child.tag in skip:
            continue
        if child.tag == TEXT:
            parts.append("".join(child.itertext()))
        else:
            _collect_text(child, parts, skip)


def _text_of(node: ElementTree.Element, skip: tuple[str, ...] = ()) -> str:
    parts: list[str] = []
    _collect_text(node, parts, skip)
    return "".join(parts).strip()


def _table_text(table: ElementTree.Element) -> str:
    """One line per row, cells tab-separated, so the table keeps its shape downstream."""
    rows = []
    for row in table.iter(ROW):
        cells = [_text_of(cell) for cell in row.iter(CELL)]
        if any(cells):
            rows.append("\t".join(cells))
    return "\n".join(rows)


def _emit_blocks(node: ElementTree.Element, out: list[str]) -> None:
    """Walk the section in document order, emitting prose and tables as separate blocks.

    Cells hold paragraphs of their own, so descending into a table would emit every cell
    twice — once as part of the table and once as a paragraph. The walk stops at a table
    and lets the table reader handle what is inside it.
    """
    for child in node:
        if child.tag == TABLE:
            if text := _table_text(child):
                out.append(text)
        elif child.tag == PARAGRAPH:
            # A table sits inside its paragraph, so the prose around it is collected first
            # with the table subtrees stepped over.
            if prose := _text_of(child, skip=(TABLE,)):
                out.append(prose)
            _emit_blocks(child, out)
        else:
            _emit_blocks(child, out)


class HwpxParser:
    source_type = SourceType.HWPX

    def parse(self, content: bytes) -> ParsedDocument:
        try:
            with ZipFile(BytesIO(content)) as archive:
                names = sorted(
                    (name for name in archive.namelist() if SECTION.match(name)),
                    key=lambda name: int(SECTION.match(name).group(1)),
                )
                sections = [archive.read(name) for name in names]
        except (BadZipFile, KeyError) as error:
            raise ParseError("Not a readable HWPX document") from error
        if not sections:
            raise ParseError("Not a readable HWPX document")

        blocks: list[str] = []
        for section in sections:
            try:
                root = ElementTree.fromstring(section)
            except ElementTree.ParseError as error:
                raise ParseError("Not a readable HWPX document") from error
            _emit_blocks(root, blocks)

        segments = [
            ParsedSegment(order_index=index, text=text, page=None, paragraph=index + 1)
            for index, text in enumerate(text for text in map(normalize_text, blocks) if text)
        ]
        if not segments:
            raise ParseError("HWPX document contains no text")
        return ParsedDocument(self.source_type, "\n\n".join(segment.text for segment in segments), segments)
