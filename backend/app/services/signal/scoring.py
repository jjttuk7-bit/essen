from __future__ import annotations

from collections.abc import Iterable

from app.models.analysis import Relation, SemanticSlot, SlotType


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def signal_ratio(*, total_tokens: int, core_tokens: int, supporting_tokens: int) -> float:
    return _ratio(core_tokens + supporting_tokens, total_tokens)


def redundancy_ratio(*, total_tokens: int, redundant_tokens: int) -> float:
    return _ratio(redundant_tokens, total_tokens)


def generic_ratio(*, total_tokens: int, generic_tokens: int, rhetorical_tokens: int) -> float:
    return _ratio(generic_tokens + rhetorical_tokens, total_tokens)


def evidence_coverage(slots: Iterable[SemanticSlot], relations: Iterable[Relation]) -> float:
    all_slots = list(slots)
    claim_ids = {slot.id for slot in all_slots if slot.slot_type == SlotType.CLAIM}
    evidence_ids = {slot.id for slot in all_slots if slot.slot_type == SlotType.EVIDENCE}
    linked_claims = {relation.from_slot_id for relation in relations if relation.relation_type == "supported_by" and relation.from_slot_id in claim_ids and relation.to_slot_id in evidence_ids}
    return _ratio(len(linked_claims), len(claim_ids))

_DECIDE_WEIGHTS = {
    SlotType.PROBLEM: 20, SlotType.OPTION: 15, SlotType.EVIDENCE: 20,
    SlotType.TRADE_OFF: 15, SlotType.RECOMMENDATION: 15, SlotType.DECISION: 10,
    SlotType.ACTION: 5,
}


def decision_completeness(purpose: str, slots: Iterable[SemanticSlot]) -> float:
    if purpose != "DECIDE":
        return 1.0
    types = {slot.slot_type for slot in slots}
    return sum(weight for slot_type, weight in _DECIDE_WEIGHTS.items() if slot_type in types) / 100


def actionability_score(slots: Iterable[SemanticSlot], relations: Iterable[Relation]) -> float:
    all_slots = list(slots)
    actions = {slot.id for slot in all_slots if slot.slot_type == SlotType.ACTION}
    if not actions:
        return 0.0
    slots_by_id = {slot.id: slot for slot in all_slots}
    required = {"owned_by": SlotType.OWNER, "due_at": SlotType.DEADLINE, "measured_by": SlotType.SUCCESS_CRITERIA}
    complete = 0
    for action_id in actions:
        relation_types = {relation.relation_type for relation in relations if relation.from_slot_id == action_id and slots_by_id.get(relation.to_slot_id, None) is not None and slots_by_id[relation.to_slot_id].slot_type == required.get(relation.relation_type)}
        if relation_types == set(required):
            complete += 1
    return _ratio(complete, len(actions))


def document_signal_score(*, signal: float, evidence: float, completeness: float, actionability: float, redundancy: float, generic: float) -> float:
    return round(0.25 * signal + 0.20 * evidence + 0.20 * completeness + 0.15 * actionability + 0.10 * (1 - redundancy) + 0.10 * (1 - generic), 6)
