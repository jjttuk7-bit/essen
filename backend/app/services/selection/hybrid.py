"""Core selection: the rule layer and the model's contextual judgement, combined.

Rules are reproducible and can name their reason but cannot tell what matters for this
particular document; the model can, but explains nothing and cannot be reproduced. Each
passage is therefore scored by both, and where they disagree the disagreement itself is
recorded — that is what the reader is shown.

Two hard constraints sit above the score. Every source section that has any candidate
keeps at least one, because a section vanishing turns a condensation into a mutilation.
And the surviving passages stay in source order, so the result reads as the same document.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from app.services.selection.rules import RuleScore, Shape, classify_shape, score_passage

RULE_WEIGHT = 0.5
MODEL_WEIGHT = 0.5
# Above this, a layer considers the passage core.
AGREEMENT_THRESHOLD = 0.5
# Below this combined score nothing is kept, even when a section still has room.
FLOOR = 0.2


class Verdict(str, Enum):
    AGREED_KEEP = "AGREED_KEEP"
    RULE_ONLY = "RULE_ONLY"
    MODEL_ONLY = "MODEL_ONLY"
    AGREED_DROP = "AGREED_DROP"


@dataclass(frozen=True)
class Selection:
    slot: object
    score: float
    rule: RuleScore
    model_importance: float
    verdict: Verdict
    reason: str


def _verdict(rule_score: float, model_importance: float) -> Verdict:
    rule_says_core = rule_score >= AGREEMENT_THRESHOLD
    model_says_core = model_importance >= AGREEMENT_THRESHOLD
    if rule_says_core and model_says_core:
        return Verdict.AGREED_KEEP
    if rule_says_core:
        return Verdict.RULE_ONLY
    if model_says_core:
        return Verdict.MODEL_ONLY
    return Verdict.AGREED_DROP


def _reason(verdict: Verdict, rule: RuleScore) -> str:
    grounds = ", ".join(rule.reasons)
    if verdict is Verdict.MODEL_ONLY:
        return f"문맥상 중요 ({grounds})"
    if verdict is Verdict.RULE_ONLY:
        return f"{grounds} — 문맥 판정은 낮음"
    return grounds


def _assess(slot: object, segment_texts: dict[str, str]) -> Selection:
    segment_id = getattr(slot, "source_segment_id", "")
    shape = classify_shape(segment_texts.get(segment_id, ""))
    text = getattr(slot, "normalized_text", "")
    rule = score_passage(text, shape)
    importance = float(getattr(slot, "importance", 0.0))
    verdict = _verdict(rule.score, importance)
    combined = round(RULE_WEIGHT * rule.score + MODEL_WEIGHT * importance, 4)
    return Selection(slot=slot, score=combined, rule=rule, model_importance=importance, verdict=verdict, reason=_reason(verdict, rule))


def _allocate(sections: dict[str, list[Selection]], budget: int) -> dict[str, int]:
    """One place per section first, then the remainder in proportion to candidate counts."""
    if not sections:
        return {}
    allocation = {heading: 1 for heading in sections}
    if budget < len(sections):
        # Too tight to cover every section; the strongest sections get the places.
        strongest = sorted(sections, key=lambda heading: -max(item.score for item in sections[heading]))
        return {heading: 1 for heading in strongest[:budget]}
    remaining = budget - len(sections)
    total = sum(len(items) for items in sections.values())
    for heading, items in sections.items():
        if remaining <= 0:
            break
        share = min(remaining, max(0, round(remaining * len(items) / total)))
        allocation[heading] += share
        remaining -= share
    return allocation


def select_core(
    slots: Sequence[object],
    *,
    segment_texts: dict[str, str],
    outline: object | None,
    budget: int,
) -> list[Selection]:
    assessed = [_assess(slot, segment_texts) for slot in slots]
    candidates = [item for item in assessed if item.score >= FLOOR]
    if not candidates:
        return []

    # Without an outline the source's own order is the input order; keeping it is what
    # makes the result read as the same document rather than a ranked list.
    arrival = {id(item): index for index, item in enumerate(assessed)}
    position = (
        (lambda item: outline.position_of(getattr(item.slot, "source_segment_id", "")))
        if outline is not None
        else (lambda item: arrival[id(item)])
    )
    heading_of = (lambda segment_id: outline.heading_for(segment_id) or "") if outline is not None else (lambda _: "")

    sections: dict[str, list[Selection]] = {}
    for item in candidates:
        sections.setdefault(heading_of(getattr(item.slot, "source_segment_id", "")), []).append(item)

    kept: list[Selection] = []
    for heading, limit in _allocate(sections, budget).items():
        ranked = sorted(sections[heading], key=lambda item: (-item.score, position(item)))
        kept.extend(ranked[:limit])

    return sorted(kept, key=position)
