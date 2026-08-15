from app.models.analysis import Relation, SemanticSlot, SlotType
from app.services.signal.scoring import actionability_score, decision_completeness, document_signal_score, evidence_coverage, signal_ratio


def test_signal_ratio_uses_only_core_and_supporting_tokens() -> None:
    assert signal_ratio(total_tokens=100, core_tokens=25, supporting_tokens=15) == 0.40


def _slot(identifier: str, slot_type: SlotType) -> SemanticSlot:
    return SemanticSlot(id=identifier, analysis_run_id="run", source_segment_id="seg", slot_type=slot_type, normalized_text=identifier, confidence=1, importance=1)


def test_quality_metrics_follow_the_documented_weights() -> None:
    slots = [_slot("claim", SlotType.CLAIM), _slot("evidence", SlotType.EVIDENCE), _slot("action", SlotType.ACTION), _slot("owner", SlotType.OWNER), _slot("deadline", SlotType.DEADLINE), _slot("criteria", SlotType.SUCCESS_CRITERIA), _slot("problem", SlotType.PROBLEM)]
    relations = [
        Relation(from_slot_id="claim", relation_type="supported_by", to_slot_id="evidence"),
        Relation(from_slot_id="action", relation_type="owned_by", to_slot_id="owner"),
        Relation(from_slot_id="action", relation_type="due_at", to_slot_id="deadline"),
        Relation(from_slot_id="action", relation_type="measured_by", to_slot_id="criteria"),
    ]
    assert evidence_coverage(slots, relations) == 1
    assert decision_completeness("DECIDE", slots) == 0.45
    assert actionability_score(slots, relations) == 1
    assert document_signal_score(signal=0.4, evidence=1, completeness=0.45, actionability=1, redundancy=0.2, generic=0.1) == 0.71