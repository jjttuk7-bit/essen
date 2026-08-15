from app.models.analysis import Relation, SemanticSlot, SlotType
from app.services.signal.scoring import actionability_score


def test_actionability_requires_all_documented_metadata_relations() -> None:
    slots = [
        SemanticSlot(id="action", analysis_run_id="run", source_segment_id="seg", slot_type=SlotType.ACTION, normalized_text="Act", confidence=1, importance=1),
        SemanticSlot(id="owner", analysis_run_id="run", source_segment_id="seg", slot_type=SlotType.OWNER, normalized_text="Team", confidence=1, importance=1),
        SemanticSlot(id="deadline", analysis_run_id="run", source_segment_id="seg", slot_type=SlotType.DEADLINE, normalized_text="Friday", confidence=1, importance=1),
        SemanticSlot(id="criteria", analysis_run_id="run", source_segment_id="seg", slot_type=SlotType.SUCCESS_CRITERIA, normalized_text="Done", confidence=1, importance=1),
    ]
    relations = [Relation(from_slot_id="action", relation_type="owned_by", to_slot_id="owner"), Relation(from_slot_id="action", relation_type="due_at", to_slot_id="deadline"), Relation(from_slot_id="action", relation_type="measured_by", to_slot_id="criteria")]
    assert actionability_score(slots, relations) == 1