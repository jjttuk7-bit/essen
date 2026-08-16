from collections.abc import Sequence
from dataclasses import dataclass
from typing import Iterable


class UnsupportedClaimError(ValueError):
    """Raised when output text cannot be traced to a semantic slot."""


@dataclass(frozen=True)
class RenderedSection:
    heading: str
    text: str
    source_slot_ids: list[str]
    source_segment_ids: list[str]


@dataclass(frozen=True)
class RenderedDocument:
    output_type: str
    sections: list[RenderedSection]

    @property
    def content(self) -> str:
        return "\n\n".join(f"{section.heading}\n{section.text}" for section in self.sections)

    @property
    def provenance(self) -> list[dict[str, object]]:
        return [{"heading": section.heading, "text": section.text, "source_slot_ids": section.source_slot_ids, "source_segment_ids": section.source_segment_ids} for section in self.sections]


# The product's value is the reduction, so the document is capped rather than growing
# with its source.
ITEM_BUDGETS = {"clean_version": 30}


def select_by_importance(slots: Sequence[object], *, limit: int, preserve_order: bool = False) -> list[object]:
    """Keep the highest-importance slots, dropping the rest.

    Ranking decides what survives; `preserve_order` then restores source order so the
    reader still meets the surviving items in the sequence the document used.
    """
    ordered = sorted(enumerate(slots), key=lambda pair: (-float(getattr(pair[1], "importance", 0.0)), pair[0]))
    selected = ordered[:limit]
    if preserve_order:
        selected = sorted(selected, key=lambda pair: pair[0])
    return [slot for _, slot in selected]


def slot_value(slot: object) -> str:
    value = getattr(slot, "slot_type")
    return getattr(value, "value", str(value))


def make_section(heading: str, slots: Iterable[object]) -> RenderedSection | None:
    """One line per slot, index-aligned with the source id lists.

    Readers need discrete items rather than one run-on paragraph, and keeping exactly one
    line per slot lets a line be traced back to the slot and segment at the same index.
    """
    selected = list(slots)
    if not selected:
        return None
    return RenderedSection(
        heading=heading,
        text="\n".join(" ".join(getattr(slot, "normalized_text").split()) for slot in selected),
        source_slot_ids=[getattr(slot, "id") for slot in selected],
        source_segment_ids=[getattr(slot, "source_segment_id") for slot in selected],
    )
