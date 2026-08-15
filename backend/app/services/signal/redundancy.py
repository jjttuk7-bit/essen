from __future__ import annotations

import re
from collections.abc import Iterable


def normalize_text(text: str) -> str:
    """Normalize only casing, punctuation, and whitespace for exact duplicate detection."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", text.casefold())).strip()


def find_redundant_segments(segments: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    """Mark later exact normalized duplicates; source text is never removed."""
    first_by_text: dict[str, str] = {}
    labels: list[tuple[str, str]] = []
    for segment_id, text in segments:
        normalized = normalize_text(text)
        if not normalized:
            continue
        original_id = first_by_text.get(normalized)
        if original_id is None:
            first_by_text[normalized] = segment_id
        else:
            labels.append((segment_id, f"동일 의미가 {original_id}에 더 구체적으로 존재함"))
    return labels
