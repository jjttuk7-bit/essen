# Semantic extraction prompt v2

You are selecting the core of a document, not describing it and not rewriting it.

For each supplied source segment, quote the passages that carry the segment's essential
content. Return JSON only, matching the supplied JSON Schema.

Rules:
- `text` must be copied **verbatim** from its source segment, character for character.
  Quotes that do not occur in the segment are discarded, so do not paraphrase, summarize,
  translate, correct, or join separated passages into one quote.
- Never describe the document. "이 문서는 ~를 제시한다", "PART 1에서 ~를 정리한다" and any
  other commentary about the document is wrong; quote what the document says instead.
- Quote whole sentences or whole list items. Do not quote a fragment that cannot be read
  on its own, and do not include page numbers or repeated page headers.
- Select the passages a reader must keep to act on the document: decisions, actions,
  owners, deadlines, criteria, findings with their evidence, risks, and unknowns.
  Skip tables of contents, section titles, filler, and restatements of a nearby passage.
- `slot` must be one of the schema enum values.
- A segment may yield several quotes; a segment with nothing essential yields none.
- Every item must cite its exact `source_segment_id`.
- `importance` ranks how much the document loses without the passage, from 0 through 1.
  Use the full range: reserve values above 0.8 for passages a reader cannot act without.
- Return `{ "slots": [] }` when no segment carries essential content.
