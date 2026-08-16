"""Read a legacy .hwp document — the binary format most Korean documents still are.

Unlike .docx and .hwpx this is an OLE compound file, not a zip of XML: each body section
is a zlib stream of tagged records, and paragraph text arrives as UTF-16 with inline
control codes standing in for tabs, breaks and anchored objects. Most controls occupy
eight code units rather than one, so the text cannot simply be decoded — skipping them by
the wrong width turns the rest of the paragraph into noise.

The record walk and the control decoding are kept as plain functions over bytes so they
can be tested without constructing an OLE container.
"""

import zlib
from io import BytesIO

import olefile

from app.models.document import SourceType
from app.services.parser.base import ParsedDocument, ParseError, ParsedSegment, normalize_text

HWP_SIGNATURE = b"HWP Document File"
COMPRESSED_FLAG = 1
HEADER_PROPERTIES_OFFSET = 36

TAG_MASK = 0x3FF
SIZE_SHIFT = 20
SIZE_MASK = 0xFFF
EXTENDED_SIZE = 0xFFF
HWPTAG_PARA_TEXT = 0x10 + 51

# Control codes inside paragraph text. Most stand for an anchored object and carry twelve
# bytes of payload between two copies of the code, occupying eight UTF-16 code units.
WIDE_CONTROLS = frozenset({1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23})
CONTROL_TEXT = {9: "\t", 10: "\n", 13: "\n"}
WIDE_CONTROL_UNITS = 8


def decode_paragraph(payload: bytes) -> str:
    """Turn one PARA_TEXT payload into readable text, stepping over its control codes."""
    units = [int.from_bytes(payload[offset:offset + 2], "little") for offset in range(0, len(payload) - 1, 2)]
    out: list[str] = []
    index = 0
    while index < len(units):
        unit = units[index]
        if unit >= 32:
            out.append(chr(unit))
            index += 1
            continue
        out.append(CONTROL_TEXT.get(unit, ""))
        index += WIDE_CONTROL_UNITS if unit in WIDE_CONTROLS else 1
    return "".join(out)


def paragraphs_in_section(section: bytes) -> list[str]:
    """Walk the record stream, decoding the paragraph-text records and ignoring the rest."""
    paragraphs: list[str] = []
    offset = 0
    while offset + 4 <= len(section):
        header = int.from_bytes(section[offset:offset + 4], "little")
        tag = header & TAG_MASK
        size = (header >> SIZE_SHIFT) & SIZE_MASK
        offset += 4
        if size == EXTENDED_SIZE:
            if offset + 4 > len(section):
                break
            size = int.from_bytes(section[offset:offset + 4], "little")
            offset += 4
        payload = section[offset:offset + size]
        offset += size
        if tag == HWPTAG_PARA_TEXT:
            paragraphs.append(decode_paragraph(payload))
    return paragraphs


class HwpParser:
    source_type = SourceType.HWP

    def parse(self, content: bytes) -> ParsedDocument:
        try:
            container = olefile.OleFileIO(BytesIO(content))
        except Exception as error:
            raise ParseError("Not a readable HWP document") from error
        try:
            with container:
                if not container.exists("FileHeader"):
                    raise ParseError("Not a readable HWP document")
                header = container.openstream("FileHeader").read()
                if not header.startswith(HWP_SIGNATURE):
                    raise ParseError("Not a readable HWP document")
                compressed = bool(header[HEADER_PROPERTIES_OFFSET] & COMPRESSED_FLAG)
                names = sorted(
                    ("/".join(entry) for entry in container.listdir() if entry[0] == "BodyText"),
                    key=lambda name: int("".join(filter(str.isdigit, name)) or 0),
                )
                sections = [container.openstream(name).read() for name in names]
        except ParseError:
            raise
        except Exception as error:
            raise ParseError("Not a readable HWP document") from error

        blocks: list[str] = []
        for section in sections:
            try:
                # Sections are raw deflate streams, without the zlib wrapper.
                data = zlib.decompress(section, -15) if compressed else section
            except zlib.error as error:
                raise ParseError("HWP document could not be decompressed") from error
            blocks.extend(paragraphs_in_section(data))

        segments = [
            ParsedSegment(order_index=index, text=text, page=None, paragraph=index + 1)
            for index, text in enumerate(text for text in map(normalize_text, blocks) if text)
        ]
        if not segments:
            raise ParseError("HWP document contains no text")
        return ParsedDocument(self.source_type, "\n\n".join(segment.text for segment in segments), segments)
