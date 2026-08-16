"""Recover a document's own heading structure from its segments.

A condensed document should read like a shorter version of the original, so it has to keep
the original's sections and their order. Extracted text carries no markup, so the headings
are recovered from the text itself: repeated page furniture is discarded, then the leading
line of a segment is taken as a heading when it looks like one.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

# A bare marker line ("PART 1") carries no title, so the following line completes it.
MARKER_PATTERNS = (
    re.compile(r"^PART\s*\d+\b", re.IGNORECASE),
    re.compile(r"^CHAPTER\s*\d+\b", re.IGNORECASE),
    re.compile(r"^제?\s*\d+\s*(장|부|절)\b"),
    re.compile(r"^\d+(\.\d+)*[.)]\s+\S"),
    re.compile(r"^#{1,6}\s+\S"),
    # Minutes number their agenda rather than their chapters.
    re.compile(r"^(안건|의안)\s*\d+"),
)
NAMED_SECTIONS = ("목차", "서문", "머리말", "맺음말", "부록", "개요", "배경", "요약", "결론", "들어가며", "나가며")
BARE_MARKER = re.compile(r"^(PART|CHAPTER)\s*\d+$", re.IGNORECASE)
# Page furniture repeats across the document; a line on this many segments is not a heading.
BOILERPLATE_SHARE = 0.25
MAX_HEADING_LENGTH = 60


@dataclass(frozen=True)
class DocumentOutline:
    ordered_headings: list[str]
    _by_segment: dict[str, str]
    _positions: dict[str, int]

    def heading_for(self, segment_id: str) -> str | None:
        return self._by_segment.get(segment_id)

    def position_of(self, segment_id: str) -> int:
        """Where the segment sits in the source, used to keep sections in document order."""
        return self._positions.get(segment_id, len(self._positions))


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.split("\n") if line.strip()]


def _boilerplate(segments: Sequence[object]) -> set[str]:
    counts: dict[str, int] = {}
    for segment in segments:
        for line in set(_lines(getattr(segment, "text"))):
            counts[line] = counts.get(line, 0) + 1
    threshold = max(2, int(len(segments) * BOILERPLATE_SHARE))
    return {line for line, count in counts.items() if count >= threshold and len(line) <= MAX_HEADING_LENGTH}


def _looks_like_heading(line: str) -> bool:
    if len(line) > MAX_HEADING_LENGTH:
        return False
    if any(pattern.match(line) for pattern in MARKER_PATTERNS):
        return True
    return any(line.startswith(name) for name in NAMED_SECTIONS)


def _clean(line: str) -> str:
    return re.sub(r"^#{1,6}\s+", "", line).strip()


def _is_bare(heading: str) -> bool:
    """A numbered label carries no title of its own, so the next line completes it.

    Named sections ("서문", "목차") are already a full heading; joining them to the line
    below would swallow the first line of the body.
    """
    return bool(BARE_MARKER.match(heading))


def build_outline(segments: Sequence[object]) -> DocumentOutline:
    ordered = sorted(segments, key=lambda segment: getattr(segment, "order_index"))
    boilerplate = _boilerplate(ordered)

    headings: list[str] = []
    by_segment: dict[str, str] = {}
    positions = {getattr(segment, "id"): index for index, segment in enumerate(ordered)}
    current: str | None = None

    for segment in ordered:
        candidates = [line for line in _lines(getattr(segment, "text")) if line not in boilerplate and not line.isdigit()]
        if candidates and _looks_like_heading(candidates[0]):
            heading = _clean(candidates[0])
            # "PART 1" alone names nothing; the title sits on the next line.
            if _is_bare(heading) and len(candidates) > 1 and len(candidates[1]) <= MAX_HEADING_LENGTH:
                heading = f"{heading} {_clean(candidates[1])}"
            current = heading
            if heading not in headings:
                headings.append(heading)
        if current is not None:
            by_segment[getattr(segment, "id")] = current

    return DocumentOutline(ordered_headings=headings, _by_segment=by_segment, _positions=positions)
