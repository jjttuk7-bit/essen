# Semantic extraction prompt v1

Extract every supported semantic item from each supplied source segment. Return JSON only, matching the supplied JSON Schema.

Rules:
- `slot` must be one of the schema enum values.
- A segment may yield multiple labels; do not collapse labels to one per segment.
- Every item must cite its exact `source_segment_id`.
- Do not infer or create facts that are absent from the source segment.
- Use confidence and importance values from 0 through 1.
- Return `{ "slots": [] }` when no supported items exist.
