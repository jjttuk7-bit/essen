from collections.abc import Iterable

from app.models.analysis import Relation, SemanticSlot, SlotType


# Relations are intentionally conservative: both slots must be anchored in the
# same source segment and match an explicit semantic direction.
RELATION_RULES: dict[tuple[SlotType, SlotType], str] = {
    (SlotType.FACT, SlotType.EVIDENCE): "supported_by",
    (SlotType.CLAIM, SlotType.EVIDENCE): "supported_by",
    (SlotType.DECISION, SlotType.ACTION): "triggers",
    (SlotType.ACTION, SlotType.OWNER): "owned_by",
}


def build_documented_relations(slots: Iterable[SemanticSlot]) -> list[Relation]:
    """Create explicit source-supported directional relationships only."""
    all_slots = list(slots)
    return [
        Relation(from_slot_id=left.id, relation_type=relation_type, to_slot_id=right.id)
        for left in all_slots
        for right in all_slots
        if left.id != right.id
        and left.source_segment_id == right.source_segment_id
        and (relation_type := RELATION_RULES.get((left.slot_type, right.slot_type)))
    ]
