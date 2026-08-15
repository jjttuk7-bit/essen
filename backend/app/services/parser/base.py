from __future__ import annotations

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
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def segments_for_text(text: str, *, page: int | None = None, start_paragraph: int = 1) -> list[ParsedSegment]:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    return [
        ParsedSegment(index, paragraph, page, start_paragraph + index)
        for index, paragraph in enumerate(paragraphs)
    ]
