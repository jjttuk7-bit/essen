"""OpenAI structured outputs with strict: true accept only a subset of JSON Schema.

Pydantic's model_json_schema() violates it (optional properties omitted from required,
minLength/minimum/maximum/prefixItems keywords), which OpenAI rejects with a bare 400.
These tests pin the hand-written wire schema to those rules and to the model it decodes into.
"""

from app.schemas.semantic import SemanticSlotPayload, ValidatedAnalysis
from app.services.llm.strict_schema import ANALYSIS_JSON_SCHEMA

UNSUPPORTED_KEYWORDS = {"minLength", "maxLength", "minimum", "maximum", "prefixItems", "minItems", "maxItems", "default", "format", "pattern"}


def _objects(node: object) -> list[dict]:
    found: list[dict] = []
    if isinstance(node, dict):
        if node.get("type") == "object":
            found.append(node)
        for value in node.values():
            found.extend(_objects(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_objects(item))
    return found


def _keywords(node: object) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        found |= set(node)
        for value in node.values():
            found |= _keywords(value)
    elif isinstance(node, list):
        for item in node:
            found |= _keywords(item)
    return found


def test_every_object_forbids_additional_properties() -> None:
    assert all(node.get("additionalProperties") is False for node in _objects(ANALYSIS_JSON_SCHEMA))


def test_every_property_is_required() -> None:
    for node in _objects(ANALYSIS_JSON_SCHEMA):
        assert set(node.get("required", [])) == set(node.get("properties", {})), node.get("title", node)


def test_no_unsupported_keywords_are_present() -> None:
    assert not _keywords(ANALYSIS_JSON_SCHEMA) & UNSUPPORTED_KEYWORDS


def test_the_wire_schema_matches_the_model_it_decodes_into() -> None:
    """Guards against drift: a field added to the model must reach the provider contract."""
    root = ANALYSIS_JSON_SCHEMA["properties"]
    assert set(root) == set(ValidatedAnalysis.model_fields)

    slot = root["slots"]["items"]["properties"]
    assert set(slot) == set(SemanticSlotPayload.model_fields)


def test_the_slot_enum_matches_the_model_slot_types() -> None:
    from app.models.analysis import SlotType

    assert set(ANALYSIS_JSON_SCHEMA["properties"]["slots"]["items"]["properties"]["slot"]["enum"]) == {slot.value for slot in SlotType}


def test_a_provider_payload_shaped_by_the_schema_validates() -> None:
    analysis = ValidatedAnalysis.model_validate(
        {"slots": [{"slot": "FACT", "text": "Revenue grew 20%.", "source_segment_id": "segment-1", "source_span": None, "confidence": 0.9, "importance": 0.8, "evidence_links": []}]}
    )

    assert analysis.slots[0].slot.value == "FACT"
