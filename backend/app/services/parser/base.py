from __future__ import annotations

import re
import statistics

from dataclasses import dataclass
from typing import Protocol

from app.models.document import SourceType


class ParseError(ValueError):
    """Raised when an uploaded source cannot produce usable text."""


@dataclass(frozen=True)
class ParsedSegment:
    order_index: int
    text: str
    page: int | None
    paragraph: int

    @property
    def token_count(self) -> int:
        return len(self.text.split())


@dataclass(frozen=True)
class ParsedDocument:
    source_type: SourceType
    raw_text: str
    segments: list[ParsedSegment]


class SourceParser(Protocol):
    source_type: SourceType

    def parse(self, content: bytes) -> ParsedDocument: ...


def normalize_text(text: str) -> str:
    # PDF extraction can emit NUL characters, which PostgreSQL rejects in text literals.
    # SQLite accepts them, so this only surfaces once a deployment points at Postgres.
    return text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n").strip()


# A line that opens a new unit rather than continuing the previous one.
_OPENS_BLOCK = re.compile(
    r"^\s*(?:[•·▪◦●○]|[-*+]\s|\d+[.)]\s|[①-⑳]|[가-힣]\.\s|#{1,6}\s"
    r"|제\s*\d+\s*[조장절항]|PART\s*\d|CHAPTER\s*\d|안건\s*\d|[A-Z]{1,3}-\d+\b)",
    re.IGNORECASE,
)
# A line ending in sentence-final punctuation has finished its thought.
_CLOSES_SENTENCE = re.compile(r"(?:다|요|음|함|임)[.!?]?[\"'”’)\]]?\s*$|[.!?][\"'”’)\]]?\s*$")
# Below this a run of lines is a paragraph, not a page that lost its blank lines.
_UNBROKEN_MIN_LINES = 4
# A wrapped line is long by definition — it filled the column. Where the typical line
# is short, extraction is already emitting one item per line and recovering breaks by
# column width would only fragment a list or a flattened table.
_WRAPPED_PROSE_MEDIAN = 20
# The column width, read off the document's own lines rather than assumed.
_WRAP_WIDTH_QUANTILE = 0.9
_WRAP_WIDTH_RATIO = 0.85
_HANGUL = re.compile(r"[가-힣]")


def _split_unbroken(block: str) -> list[str]:
    """Recover paragraph breaks from a block that arrived without any.

    Extraction often yields a whole page as one run of lines. Splitting on every line
    would break wrapped sentences apart, so a line starts a new paragraph only when it
    opens a new unit — a bullet, a number, a heading — or when the line before it closed
    its sentence.
    """
    lines = [line.strip() for line in block.split("\n") if line.strip()]
    if len(lines) < _UNBROKEN_MIN_LINES:
        return [block.strip()]
    if statistics.median(len(line) for line in lines) < _WRAPPED_PROSE_MEDIAN:
        return [block.strip()]

    # A line that stopped short of the column width ended because its content ended, not
    # because it ran out of room, so only a full line can continue onto the next.
    widths = sorted(len(line) for line in lines)
    wrap_width = widths[int(len(widths) * _WRAP_WIDTH_QUANTILE) - 1] * _WRAP_WIDTH_RATIO

    paragraphs: list[list[str]] = []
    for line in lines:
        previous = paragraphs[-1][-1] if paragraphs else ""
        continues = (
            bool(paragraphs)
            and len(previous) >= wrap_width
            and not _CLOSES_SENTENCE.search(previous)
            and not _OPENS_BLOCK.match(line)
        )
        if continues:
            paragraphs[-1].append(line)
        else:
            paragraphs.append([line])
    return [_join_wrapped(paragraph) for paragraph in paragraphs]


def _join_wrapped(lines: list[str]) -> str:
    """Rejoin wrapped lines, adding a space only where the break implies one.

    Korean lines break anywhere, so the break usually falls inside a word and inserting a
    space would split it. Latin text breaks between words, where the space was the break.
    """
    joined = lines[0]
    for line in lines[1:]:
        both_korean = _HANGUL.match(joined[-1]) and _HANGUL.match(line[0])
        joined += line if both_korean else f" {line}"
    return joined


def segments_for_text(text: str, *, page: int | None = None, start_paragraph: int = 1) -> list[ParsedSegment]:
    blocks = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    # Recovering breaks is for text that has none. Where blank lines already mark the
    # paragraphs, they are the author's own and splitting further only fragments them.
    paragraphs = _split_unbroken(blocks[0]) if len(blocks) == 1 else blocks
    return [
        ParsedSegment(index, paragraph, page, start_paragraph + index)
        for index, paragraph in enumerate(paragraphs)
    ]
