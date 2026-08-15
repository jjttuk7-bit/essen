# Document Intelligence MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an auditable MVP that turns a text, Markdown, or text-extractable PDF into a diagnosis, semantic map, and three human-ready document outputs without inventing source facts.

**Architecture:** A FastAPI service owns document storage, deterministic parsing/scoring, validated LLM analysis, and rendering with provenance. A Next.js UI uploads a document, polls/requests analysis, then presents the diagnosis, semantic slots, generated outputs, and explanation-backed diffs. SQLite is used locally through SQLAlchemy; provider-specific LLM behavior is isolated behind an adapter interface.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, SQLite, pytest; Next.js (App Router), TypeScript, React, Tailwind CSS, Vitest, Playwright.

---

## Confirmed scope and decisions

- Support TXT, Markdown, and text-layer PDF first. Reject scanned PDFs with a clear error rather than adding OCR to MVP.
- Persist each document's raw text, ordered segments, analysis provenance, raw model response, and prompt version.
- Make local development usable without credentials by supplying a deterministic `RuleBasedLLMAdapter`; enable an OpenAI-compatible adapter only when configured.
- Keep automation advisory: every delete/merge/unsupported decision must carry a reason and source segment IDs.
- Deliver the three specified outputs: `clean_version`, `executive_summary`, and `action_decision_sheet`.
- Defer external fact checking, authentication, collaboration, OCR, and multi-document workflows per `08_MVP_SCOPE.md`.

## Repository layout to create

```text
backend/
  app/{api,core,models,prompts,schemas,services/{llm,parser,semantic,signal,renderer}}/
  tests/{api,services}/
  alembic/
frontend/
  app/{page.tsx,documents/[id]/page.tsx}/
  components/
  lib/
  tests/
docs/{plans,adr}/
```

## Task 1: Establish the backend skeleton and reproducible local setup

**Files:**
- Create: `backend/pyproject.toml`, `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/api/router.py`
- Create: `backend/tests/test_health.py`, `backend/.env.example`, `README.md`

**Step 1: Write the failing health test**

```python
from fastapi.testclient import TestClient
from app.main import create_app

def test_health_returns_service_status():
    response = TestClient(create_app()).get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
```

**Step 2: Run it to verify it fails**

Run: `cd backend && uv run pytest tests/test_health.py -v`

Expected: failure because `app.main` does not exist.

**Step 3: Implement the minimal application factory**

```python
def create_app() -> FastAPI:
    app = FastAPI(title='Human Layer API')
    app.include_router(router)
    return app
```

Add `GET /health` returning `{'status': 'ok'}`. Pin runtime/test dependencies in `pyproject.toml`; document exact start commands and environment variables in the root README.

**Step 4: Run the test**

Run: `cd backend && uv run pytest tests/test_health.py -v`

Expected: PASS.

**Step 5: Commit**

`git add backend README.md && git commit -m "chore: initialize document intelligence API"`

## Task 2: Model documents, segments, and audit records

**Files:**
- Create: `backend/app/core/database.py`, `backend/app/models/base.py`, `backend/app/models/document.py`, `backend/app/models/analysis.py`
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_initial_schema.py`
- Test: `backend/tests/models/test_document_models.py`

**Step 1: Write model persistence tests**

```python
def test_document_keeps_ordered_source_segments(session):
    document = Document(title='Plan', source_type='markdown', raw_text='# Plan')
    document.segments = [Segment(order_index=0, text='# Plan', token_count=2)]
    session.add(document); session.commit()
    assert session.get(Document, document.id).segments[0].text == '# Plan'
```

**Step 2: Run the focused test**

Run: `cd backend && uv run pytest tests/models/test_document_models.py -v`

Expected: FAIL because the models are absent.

**Step 3: Implement SQLAlchemy models and migration**

Create `Document`, `Segment`, `SemanticSlot`, `Relation`, `QualityLabel`, `Gap`, `RenderedOutput`, and `AnalysisRun`. Require `source_segment_id` on slots and output provenance; record `prompt_version` and `raw_model_output` on every LLM-backed analysis run.

**Step 4: Verify migration and tests**

Run: `cd backend && uv run alembic upgrade head && uv run pytest tests/models/test_document_models.py -v`

Expected: migration succeeds; test PASS.

**Step 5: Commit**

`git add backend && git commit -m "feat: add auditable document analysis schema"`

## Task 3: Parse uploads and segment source text

**Files:**
- Create: `backend/app/services/parser/{base.py,text.py,markdown.py,pdf.py,service.py}`
- Create: `backend/app/schemas/document.py`, `backend/app/api/documents.py`
- Test: `backend/tests/services/parser/test_segmentation.py`, `backend/tests/api/test_document_upload.py`

**Step 1: Write failing examples for paragraph boundaries and PDF rejection**

```python
def test_parser_assigns_stable_order_and_paragraph_number():
    segments = parse_text('First paragraph.\n\nSecond paragraph.')
    assert [(s.order_index, s.paragraph) for s in segments] == [(0, 1), (1, 2)]

def test_scanned_pdf_is_rejected_when_no_text_is_extractable(client):
    response = client.post('/documents', files={'file': ('scan.pdf', b'%PDF...', 'application/pdf')})
    assert response.status_code == 422
```

**Step 2: Run the tests and confirm failure**

Run: `cd backend && uv run pytest tests/services/parser tests/api/test_document_upload.py -v`

**Step 3: Implement `POST /documents`**

Validate file type/size, extract text with `pypdf`, normalize line endings without altering meaning, create ordered segments with page/paragraph metadata, and store the document transactionally. Return `201` with `document_id`, source type, and segment count.

**Step 4: Run focused tests**

Run: `cd backend && uv run pytest tests/services/parser tests/api/test_document_upload.py -v`

Expected: PASS.

**Step 5: Commit**

`git add backend && git commit -m "feat: upload and segment source documents"`

## Task 4: Define strict semantic schemas and an interchangeable LLM adapter

**Files:**
- Create: `backend/app/schemas/{semantic.py,llm.py}`, `backend/app/services/llm/{base.py,rule_based.py,openai_compatible.py,factory.py}`
- Create: `backend/app/prompts/semantic_extraction_v1.md`
- Test: `backend/tests/services/llm/test_schema_validation.py`, `backend/tests/services/llm/test_adapter_factory.py`

**Step 1: Write failing validation tests**

```python
def test_slot_requires_a_known_type_and_existing_source_segment():
    with pytest.raises(ValidationError):
        ExtractedSlot(slot_type='INVENTED', source_segment_id='', text='claim')
```

**Step 2: Run test to confirm failure**

Run: `cd backend && uv run pytest tests/services/llm -v`

**Step 3: Implement schemas and adapters**

Use literal/enumerated slot labels from `03_DOCUMENT_SEMANTIC_STANDARD.md`, including multi-label extraction. Expose `analyze(request) -> ValidatedAnalysis`; validate all provider JSON before persistence. The rule-based adapter must return deterministic classifications for fixture documents, and the provider adapter must request structured JSON only.

**Step 4: Verify no credentials are required for unit tests**

Run: `cd backend && uv run pytest tests/services/llm -v`

Expected: PASS.

**Step 5: Commit**

`git add backend && git commit -m "feat: validate semantic analysis through LLM adapter"`

## Task 5: Build the semantic extraction workflow

**Files:**
- Create: `backend/app/services/semantic/{service.py,relations.py}`
- Modify: `backend/app/api/documents.py`
- Test: `backend/tests/services/semantic/test_extraction_service.py`, `backend/tests/api/test_analyze_document.py`

**Step 1: Write a failing end-to-end semantic extraction test**

```python
def test_analysis_persists_multilabel_slots_and_provenance(client, seeded_document):
    response = client.post(f'/documents/{seeded_document.id}/analyze')
    assert response.status_code == 202
    slots = response.json()['semantic_slots']
    assert all(slot['source_segment_id'] for slot in slots)
```

**Step 2: Run test to confirm failure**

Run: `cd backend && uv run pytest tests/services/semantic tests/api/test_analyze_document.py -v`

**Step 3: Implement orchestration**

Classify purpose/audience, invoke the adapter per segment or bounded batch, validate and store slots, infer only documented relations, and persist low-confidence items for review. `POST /documents/{id}/analyze` must be idempotent per input/prompt version or explicitly create a versioned analysis run.

**Step 4: Run focused tests**

Run: `cd backend && uv run pytest tests/services/semantic tests/api/test_analyze_document.py -v`

Expected: PASS.

**Step 5: Commit**

`git add backend && git commit -m "feat: analyze documents into semantic slots"`

## Task 6: Implement signal, redundancy, gap, and score calculations

**Files:**
- Create: `backend/app/services/signal/{classification.py,redundancy.py,gaps.py,scoring.py,service.py}`
- Create: `backend/app/schemas/diagnosis.py`
- Test: `backend/tests/services/signal/{test_scoring.py,test_gaps.py,test_redundancy.py}`

**Step 1: Write parameterized scoring tests**

```python
def test_signal_ratio_uses_only_core_and_supporting_tokens():
    assert signal_ratio(total_tokens=100, core_tokens=25, supporting_tokens=15) == 0.40

def test_decide_document_without_evidence_reports_gap():
    assert 'MISSING_EVIDENCE' in find_gaps('DECIDE', slots=[])
```

**Step 2: Run them to confirm failure**

Run: `cd backend && uv run pytest tests/services/signal -v`

**Step 3: Implement deterministic calculations**

Calculate the six metrics and weighted `DocumentSignalScore` exactly as specified in `05_SIGNAL_QUALITY_ENGINE.md`. Use embedding similarity only behind a service boundary; begin with deterministic normalized-text matching plus adapter labels. Mark, never delete, redundant/generic/rhetorical/unsupported segments and always save the reason.

**Step 4: Run focused tests**

Run: `cd backend && uv run pytest tests/services/signal -v`

Expected: PASS.

**Step 5: Commit**

`git add backend && git commit -m "feat: calculate diagnosis and document quality scores"`

## Task 7: Expose diagnosis and semantic-map APIs

**Files:**
- Modify: `backend/app/api/documents.py`, `backend/app/api/router.py`
- Create: `backend/app/schemas/api.py`
- Test: `backend/tests/api/{test_diagnosis.py,test_semantic_map.py}`

**Step 1: Write failing response-contract tests**

```python
def test_diagnosis_explains_score_drivers(client, analyzed_document):
    payload = client.get(f'/documents/{analyzed_document.id}/diagnosis').json()
    assert {'signal_ratio', 'gaps', 'counts', 'explanations'} <= payload.keys()
```

**Step 2: Run to confirm failure**

Run: `cd backend && uv run pytest tests/api/test_diagnosis.py tests/api/test_semantic_map.py -v`

**Step 3: Implement read APIs**

Add `GET /documents/{id}/diagnosis` and `GET /documents/{id}/semantic-map`. Return stable response schemas, slot relations, score components, diagnosis sentences, and each label's provenance/reason. Return `404` for unknown document IDs and `409` if no completed analysis exists.

**Step 4: Run focused tests**

Run: `cd backend && uv run pytest tests/api/test_diagnosis.py tests/api/test_semantic_map.py -v`

Expected: PASS.

**Step 5: Commit**

`git add backend && git commit -m "feat: expose diagnosis and semantic map APIs"`

## Task 8: Render provenance-safe human-ready outputs

**Files:**
- Create: `backend/app/services/renderer/{base.py,clean.py,executive.py,action_decision.py,service.py}`
- Modify: `backend/app/api/documents.py`
- Test: `backend/tests/services/renderer/test_provenance.py`, `backend/tests/api/test_render.py`

**Step 1: Write a failing unsupported-claim test**

```python
def test_every_rendered_claim_has_semantic_slot_provenance(renderer, validated_slots):
    output = renderer.render('executive_summary', validated_slots)
    assert all(section.source_slot_ids for section in output.sections)
```

**Step 2: Run to confirm failure**

Run: `cd backend && uv run pytest tests/services/renderer tests/api/test_render.py -v`

**Step 3: Implement the rendering layer**

Render only validated slots. `clean_version` removes/merges marked content but lists reasons; `executive_summary` prioritizes conclusion, evidence, risk, and pending decision; `action_decision_sheet` presents decision, actions, owner/deadline/criteria, and explicit unknowns. Add `POST /documents/{id}/render` and `GET /documents/{id}/outputs`.

**Step 4: Run focused tests**

Run: `cd backend && uv run pytest tests/services/renderer tests/api/test_render.py -v`

Expected: PASS.

**Step 5: Commit**

`git add backend && git commit -m "feat: render provenance-safe human-ready outputs"`

## Task 9: Create the Next.js application shell and API client

**Files:**
- Create: `frontend/package.json`, `frontend/app/layout.tsx`, `frontend/app/page.tsx`, `frontend/lib/api.ts`
- Create: `frontend/components/{upload-form.tsx,error-state.tsx,loading-state.tsx}`
- Test: `frontend/tests/upload-form.test.tsx`

**Step 1: Write failing upload-form behavior test**

```tsx
it('submits an allowed document and navigates to its workspace', async () => {
  render(<UploadForm />)
  await userEvent.upload(screen.getByLabelText(/document/i), markdownFile)
  await userEvent.click(screen.getByRole('button', {name: /analyze/i}))
  expect(mockPush).toHaveBeenCalledWith('/documents/doc_123')
})
```

**Step 2: Run test to confirm failure**

Run: `cd frontend && npm test -- upload-form.test.tsx`

**Step 3: Implement a minimal accessible upload path**

Use client-side type/size feedback matching API limits; call `POST /documents`, then analysis, and navigate to the document workspace. Display a clear API/unsupported-PDF error state. Do not use mocked score data in production paths.

**Step 4: Run UI test**

Run: `cd frontend && npm test -- upload-form.test.tsx`

Expected: PASS.

**Step 5: Commit**

`git add frontend && git commit -m "feat: add document upload interface"`

## Task 10: Build diagnosis and semantic views

**Files:**
- Create: `frontend/app/documents/[id]/page.tsx`, `frontend/components/{diagnosis-cards.tsx,diagnosis-summary.tsx,semantic-panel.tsx,source-document.tsx}`
- Test: `frontend/tests/document-workspace.test.tsx`

**Step 1: Write a failing workspace test**

```tsx
it('shows score cards and filters semantic slots by type', async () => {
  render(<DocumentWorkspace documentId="doc_123" />)
  expect(await screen.findByText(/Signal Ratio/i)).toBeVisible()
  await userEvent.click(screen.getByRole('tab', {name: /Evidence/i}))
  expect(screen.getByText('Customer interview')).toBeVisible()
})
```

**Step 2: Run test to confirm failure**

Run: `cd frontend && npm test -- document-workspace.test.tsx`

**Step 3: Implement the first analysis workspace**

Render purpose/audience and six quality measures as comprehensible cards, the human-readable diagnosis, source segments, and tabs for the specified semantic slots. Selecting a slot must highlight its source segment and expose confidence/provenance.

**Step 4: Run UI test**

Run: `cd frontend && npm test -- document-workspace.test.tsx`

Expected: PASS.

**Step 5: Commit**

`git add frontend && git commit -m "feat: show document diagnosis and semantic map"`

## Task 11: Add output and explanation-backed diff views

**Files:**
- Create: `frontend/components/{output-selector.tsx,rendered-output.tsx,diff-view.tsx}`
- Modify: `frontend/app/documents/[id]/page.tsx`
- Test: `frontend/tests/{rendered-output.test.tsx,diff-view.test.tsx}`

**Step 1: Write failing Diff explanation test**

```tsx
it('shows the retained reason for a removal candidate', async () => {
  render(<DiffView changes={fixtureChanges} />)
  await userEvent.click(screen.getByText('삭제 후보'))
  expect(screen.getByText(/동일 의미가 seg_014에/i)).toBeVisible()
})
```

**Step 2: Run to confirm failure**

Run: `cd frontend && npm test -- rendered-output.test.tsx diff-view.test.tsx`

**Step 3: Implement output rendering and diff**

Let users request/switch output modes. Show output sections with source references; show source paragraphs as kept, removed candidate, merged, unsupported, or important. Every badge opens the persisted reason, satisfying the UX requirement that deletion rationale is visible.

**Step 4: Run UI tests**

Run: `cd frontend && npm test -- rendered-output.test.tsx diff-view.test.tsx`

Expected: PASS.

**Step 5: Commit**

`git add frontend && git commit -m "feat: add human-ready outputs and reasoned diff"`

## Task 12: Build the golden-set evaluation harness and release checks

**Files:**
- Create: `backend/evaluation/{README.md,runner.py,metrics.py}`, `backend/tests/evaluation/test_metrics.py`
- Create: `backend/evaluation/fixtures/README.md`, `.github/workflows/ci.yml`, `docs/adr/0001-mvp-architecture.md`
- Modify: `README.md`

**Step 1: Write failing evaluation metric tests**

```python
def test_removal_precision_counts_only_human_agreed_candidates():
    assert removal_precision(predicted={'a', 'b'}, human_removed={'a'}) == 0.5
```

**Step 2: Run test to confirm failure**

Run: `cd backend && uv run pytest tests/evaluation/test_metrics.py -v`

**Step 3: Implement reproducible evaluation**

Define a JSONL fixture contract following `10_EVALUATION_AND_TESTSET.md`, calculate extraction recall, removal precision, slot accuracy, and gap detection accuracy. CI must run backend formatting/lint/tests and frontend lint/unit tests; add a Playwright smoke test for upload → diagnosis → executive output. Document local commands, limitations, and the rubric for 20-document MVP acceptance.

**Step 4: Run the release verification suite**

Run:

```bash
cd backend && uv run pytest -v
cd frontend && npm run lint && npm test && npx playwright test
```

Expected: all checks PASS; the evaluation report is generated from fixtures without external LLM credentials.

**Step 5: Commit**

`git add backend frontend docs README.md .github && git commit -m "test: add evaluation harness and MVP release checks"`

## Delivery gates

1. No rendered sentence that asserts a fact lacks semantic-slot provenance.
2. Diagnosis ratios and decision completeness match deterministic unit fixtures.
3. A user can upload Markdown and complete the full workflow in one local session.
4. PDF with no extractable text gets an actionable error.
5. The initial golden set demonstrates the success thresholds from `08_MVP_SCOPE.md`: ≤10% core-information omission, ≥80% human agreement on removals, and ≥4.0/5 executive-output utility.

## Risks to resolve before production

- Prompt/model changes can alter classification results; version prompts/models and retain analysis runs before comparing outcomes.
- Similarity-based redundancy detection can remove nuance; start conservative and require visible reasons/human review for low-confidence calls.
- PDF text quality varies by source; keep OCR deliberately outside MVP and measure rejection frequency.
- The recommended plan uses Next.js because the required diagnosis/semantic/diff workspace is interaction-heavy. If speed-to-demo is the sole priority, replace Tasks 9–11 with a Streamlit implementation and retain the same backend contracts.
