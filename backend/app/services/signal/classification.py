from __future__ import annotations

from collections.abc import Iterable
import re

from app.models.analysis import QualityCategory, SemanticSlot, SlotType
from app.models.document import Segment

_GENERIC_PATTERNS = ("in general", "overall", "various", "important", "best practice")


def classify_segment(segment: Segment, slots: Iterable[SemanticSlot]) -> tuple[QualityCategory, float, str]:
    """Assign one conservative, reviewable quality category to a segment."""
    segment_slots = [slot for slot in slots if slot.source_segment_id == segment.id]
    slot_types = {slot.slot_type for slot in segment_slots}
    if slot_types & {SlotType.CLAIM, SlotType.PROBLEM, SlotType.DECISION, SlotType.RECOMMENDATION, SlotType.ACTION}:
        return QualityCategory.CORE_SIGNAL, 1.0, "핵심 주장·문제·결정 또는 실행 정보가 확인됨"
    if slot_types & {SlotType.FACT, SlotType.EVIDENCE, SlotType.OPTION, SlotType.TRADE_OFF, SlotType.OWNER, SlotType.DEADLINE, SlotType.SUCCESS_CRITERIA}:
        return QualityCategory.SUPPORTING_SIGNAL, 0.8, "핵심 내용을 뒷받침하는 사실·근거 또는 실행 정보가 확인됨"
    normalized = re.sub(r"\s+", " ", segment.text).strip().lower()
    if normalized and any(pattern in normalized for pattern in _GENERIC_PATTERNS):
        return QualityCategory.GENERIC, 0.7, "구체적 근거나 실행 정보가 없는 일반론적 표현"
    if normalized.endswith("!"):
        return QualityCategory.RHETORICAL, 0.6, "강조 표현이지만 검증 가능한 정보가 확인되지 않음"
    return QualityCategory.CONTEXT, 0.5, "문맥 정보로 보수적으로 분류됨"
