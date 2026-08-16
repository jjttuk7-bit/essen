"""Wire schema for OpenAI structured outputs.

Written by hand rather than derived from `ValidatedAnalysis.model_json_schema()`: strict
mode accepts only a subset of JSON Schema, and Pydantic emits constructs outside it
(optional properties absent from `required`, plus `minLength`/`minimum`/`prefixItems`).
Sending the Pydantic output makes OpenAI reject the whole request with a bare 400.

Strict mode still requires every property to appear in `required`, so genuinely optional
fields are declared nullable and the model supplies the default when the provider sends
null. `tests/services/llm/test_strict_schema.py` guards this against model drift.
"""

from app.models.analysis import SlotType

ANALYSIS_JSON_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["slots"],
    "properties": {
        "slots": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["slot", "text", "source_segment_id", "source_span", "confidence", "importance", "evidence_links"],
                "properties": {
                    "slot": {"type": "string", "enum": [slot.value for slot in SlotType]},
                    "text": {"type": "string", "description": "The normalized semantic content, quoted or tightly paraphrased from the source segment."},
                    "source_segment_id": {"type": "string", "description": "The id of the request segment this content came from. Must match one of the supplied segments."},
                    "source_span": {"type": ["array", "null"], "items": {"type": "integer"}, "description": "Optional [start, end] character offsets within the source segment, or null."},
                    "confidence": {"type": "number", "description": "How certain the extraction is, between 0 and 1."},
                    "importance": {"type": "number", "description": "How central this content is to the document, between 0 and 1."},
                    "evidence_links": {"type": "array", "items": {"type": "string"}, "description": "Ids of other segments that support this content. Empty array when none."},
                },
            },
        }
    },
}
