# Clinical Decision Workspace Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the editorial landing/result screens with an accessible, light clinical decision workspace that makes document evidence, diagnosis, and rendered outputs usable.

**Architecture:** Keep all existing FastAPI endpoints and routes unchanged. Refactor the Next.js presentation layer around a shared token system, then extend the existing API client and result component to load and present the already available rendered outputs. The result page stays client-rendered because it already coordinates diagnosis and semantic-map requests.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript, CSS, Vitest, Testing Library.

---

### Task 1: Establish workspace tokens and responsive shell

**Files:**
- Modify: `app/globals.css`
- Test: `frontend/components/upload-form.test.tsx`

**Step 1: Write the failing test**

Add a home-page-facing assertion to the existing upload form suite that verifies the primary action uses an accessible name and the status area remains available while work is pending.

```tsx
expect(screen.getByRole("button", { name: /analyze document/i })).toBeEnabled();
expect(screen.getByText(/문서를 읽고 있습니다/)).toHaveAttribute("aria-live", "polite");
```

**Step 2: Run test to verify it fails**

Run: `npm test -- --run frontend/components/upload-form.test.tsx`

Expected: FAIL until the revised status copy and test fixture are in place.

**Step 3: Implement the minimal styling system**

Replace the warm-paper/serif/offset-shadow variables in `app/globals.css` with the approved canvas, surface, ink, muted, hairline, signal, warning, and error tokens. Define reusable styles for the application header, work cards, score tiles, source references, segmented controls, focus rings, and mobile breakpoints. Keep reduced-motion behavior.

**Step 4: Run test to verify it passes**

Run: `npm test -- --run frontend/components/upload-form.test.tsx`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/globals.css frontend/components/upload-form.test.tsx
git commit -m "style: establish clinical decision workspace tokens"
```

### Task 2: Recompose the document upload workbench

**Files:**
- Modify: `app/page.tsx`
- Modify: `frontend/components/upload-form.tsx`
- Modify: `frontend/components/upload-form.test.tsx`

**Step 1: Write the failing test**

Add coverage for a selected-file summary and upload progress. Preserve the existing duplicate-submit test.

```tsx
selectTextFile();
expect(screen.getByText("brief.txt")).toBeVisible();
fireEvent.submit(form);
expect(await screen.findByText(/문서를 읽고 있습니다/)).toBeVisible();
```

**Step 2: Run test to verify it fails**

Run: `npm test -- --run frontend/components/upload-form.test.tsx`

Expected: FAIL if the revised workbench wording/status is not implemented.

**Step 3: Implement the minimal workbench**

Refactor `app/page.tsx` into a compact product header, a task-first upload card, and a three-item capability strip. Update `UploadForm` labels/copy so the primary action reads naturally in Korean while retaining a stable accessible name, selected file size, busy status, and error alert. Do not change upload/analyze routing or API calls.

**Step 4: Run test to verify it passes**

Run: `npm test -- --run frontend/components/upload-form.test.tsx`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/page.tsx frontend/components/upload-form.tsx frontend/components/upload-form.test.tsx
git commit -m "feat: redesign document upload workbench"
```

### Task 3: Add typed rendered-output client access

**Files:**
- Modify: `lib/api.ts`
- Modify: `lib/api.test.ts`

**Step 1: Write the failing test**

Add an API-client test asserting that `getOutputs("doc-1")` requests the existing `GET /documents/doc-1/outputs` endpoint and exposes section source IDs.

```ts
await getOutputs("doc-1");
expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/documents/doc-1/outputs"), expect.objectContaining({ method: "GET" }));
```

**Step 2: Run test to verify it fails**

Run: `npm test -- --run lib/api.test.ts`

Expected: FAIL because `getOutputs` and its types do not exist.

**Step 3: Implement the minimal client contract**

Add `RenderedSection`, `RenderedOutput`, and `RenderResponse` TypeScript types matching `backend/app/schemas/api.py`, including `source_slot_ids`, `source_segment_ids`, version, audience, and max_words. Add `getOutputs(documentId)` using the existing request helper.

**Step 4: Run test to verify it passes**

Run: `npm test -- --run lib/api.test.ts`

Expected: PASS.

**Step 5: Commit**

```bash
git add lib/api.ts lib/api.test.ts
git commit -m "feat: load rendered document outputs"
```

### Task 4: Build the decision result workspace and output switcher

**Files:**
- Modify: `frontend/components/diagnosis-workspace.tsx`
- Modify: `frontend/components/diagnosis-workspace.test.tsx`
- Modify: `frontend/components/diagnosis-workspace.error.test.tsx`
- Modify: `app/globals.css`

**Step 1: Write the failing test**

Mock `getOutputs` with clean, executive, and action results. Assert that a rendered section displays its text and traceable source segment reference; assert changing the mode control shows the chosen output.

```tsx
expect(await screen.findByRole("tab", { name: /executive brief/i })).toBeVisible();
fireEvent.click(screen.getByRole("tab", { name: /action sheet/i }));
expect(screen.getByText("Owner: Operations")).toBeVisible();
expect(screen.getByText(/Source S-03/)).toBeVisible();
```

**Step 2: Run test to verify it fails**

Run: `npm test -- --run frontend/components/diagnosis-workspace.test.tsx frontend/components/diagnosis-workspace.error.test.tsx`

Expected: FAIL because the output request and tabbed evidence panel do not exist.

**Step 3: Implement the minimal workspace**

Load diagnosis, semantic map, and outputs together. Lay out score/readiness and gaps as a summary rail, semantic slots as an evidence ledger, and output modes as an accessible `role="tablist"` with a matching tab panel. Render section headings/text and `source_segment_ids` as visible references. If no outputs are present, show a calm empty state without failing the diagnosis view. Preserve current loading/error handling; make an output-request error visible with the existing alert behavior.

**Step 4: Run tests to verify they pass**

Run: `npm test -- --run frontend/components/diagnosis-workspace.test.tsx frontend/components/diagnosis-workspace.error.test.tsx`

Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/components/diagnosis-workspace.tsx frontend/components/diagnosis-workspace.test.tsx frontend/components/diagnosis-workspace.error.test.tsx app/globals.css
git commit -m "feat: build evidence-backed decision workspace"
```

### Task 5: Final accessibility and production verification

**Files:**
- Verify only

**Step 1: Run the complete frontend suite**

Run: `npm test`

Expected: PASS.

**Step 2: Build the production dashboard**

Run: `npm run build`

Expected: successful Next.js build with `/` static and `/documents/[id]` dynamic.

**Step 3: Run backend regression suite**

Run: `cd backend; uv run pytest -q`

Expected: PASS with no API regressions.

**Step 4: Check the change set**

Run: `git diff --check`

Expected: no whitespace errors.

**Step 5: Commit**

```bash
git status --short
git log --oneline -5
```

Expected: only the intentional, already committed UI redesign changes remain.

