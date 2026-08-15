from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum

from app.models.analysis import SemanticSlot, SlotType


class GapType(StrEnum):
    MISSING_PROBLEM = "MISSING_PROBLEM"
    MISSING_OPTION = "MISSING_OPTION"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    MISSING_TRADE_OFF = "MISSING_TRADE_OFF"
    MISSING_DECISION_OR_RECOMMENDATION = "MISSING_DECISION_OR_RECOMMENDATION"
    MISSING_ACTION = "MISSING_ACTION"
    MISSING_OWNER = "MISSING_OWNER"
    MISSING_DEADLINE = "MISSING_DEADLINE"
    MISSING_SUCCESS_CRITERIA = "MISSING_SUCCESS_CRITERIA"


def find_gaps(purpose: str, slots: Iterable[SemanticSlot]) -> list[str]:
    """Return purpose-specific information gaps without inferring absent facts."""
    types = {slot.slot_type if isinstance(slot.slot_type, SlotType) else SlotType(slot.slot_type) for slot in slots}
    gaps: list[GapType] = []
    if purpose == "DECIDE":
        if SlotType.PROBLEM not in types:
            gaps.append(GapType.MISSING_PROBLEM)
        if SlotType.OPTION not in types:
            gaps.append(GapType.MISSING_OPTION)
        if SlotType.TRADE_OFF not in types:
            gaps.append(GapType.MISSING_TRADE_OFF)
        if SlotType.EVIDENCE not in types:
            gaps.append(GapType.MISSING_EVIDENCE)
        if not types & {SlotType.DECISION, SlotType.RECOMMENDATION}:
            gaps.append(GapType.MISSING_DECISION_OR_RECOMMENDATION)
        if SlotType.ACTION not in types:
            gaps.append(GapType.MISSING_ACTION)
    if purpose == "PLAN":
        if SlotType.ACTION not in types:
            gaps.append(GapType.MISSING_ACTION)
        if SlotType.OWNER not in types:
            gaps.append(GapType.MISSING_OWNER)
        if SlotType.DEADLINE not in types:
            gaps.append(GapType.MISSING_DEADLINE)
        if SlotType.SUCCESS_CRITERIA not in types:
            gaps.append(GapType.MISSING_SUCCESS_CRITERIA)
    return [gap.value for gap in gaps]


def gap_description(gap_type: str) -> str:
    return {
        GapType.MISSING_PROBLEM: "판단 대상 문제가 명시되지 않았습니다.",
        GapType.MISSING_OPTION: "비교 가능한 대안이 없습니다.",
        GapType.MISSING_EVIDENCE: "핵심 판단을 뒷받침하는 근거가 없습니다.",
        GapType.MISSING_TRADE_OFF: "대안 간 장단점 또는 비용 비교가 없습니다.",
        GapType.MISSING_DECISION_OR_RECOMMENDATION: "결정 또는 권고가 명시되지 않았습니다.",
        GapType.MISSING_ACTION: "후속 실행 항목이 명시되지 않았습니다.",
        GapType.MISSING_OWNER: "실행 책임자가 명시되지 않았습니다.",
        GapType.MISSING_DEADLINE: "실행 기한이 명시되지 않았습니다.",
        GapType.MISSING_SUCCESS_CRITERIA: "완료 또는 성공 기준이 명시되지 않았습니다.",
    }[GapType(gap_type)]
