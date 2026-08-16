from dataclasses import dataclass

REMOVED = "REMOVED"
MERGED = "MERGED"
EMPHASIZED = "EMPHASIZED"
HELD = "HELD"

DISPOSITIONS = (REMOVED, MERGED, EMPHASIZED, HELD)


@dataclass(frozen=True)
class DiffEntry:
    """One source segment and what the rendered output did with it."""

    segment_id: str
    order_index: int
    original_text: str
    disposition: str
    reason: str
    rendered_headings: tuple[str, ...]
