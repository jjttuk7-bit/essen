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
