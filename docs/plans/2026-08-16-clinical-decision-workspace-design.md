# Clinical Decision Workspace Design

## Intent

Human Layer turns long source documents into evidence-backed decisions and actions. The interface must feel like a dependable decision instrument, not a magazine landing page. It will replace the current warm-paper editorial treatment with a bright, composed workspace inspired by Refero's Ui clinical blueprint and Linear's precision system.

## Design direction

- Light neutral canvas, white work surfaces, dark ink text, and one restrained teal signal accent.
- Korean-first functional typography: a readable sans-serif system for all product UI, with no oversized decorative serif headline.
- Fine borders, modest radius, and calm elevation. Information hierarchy, not shadow or ornament, conveys structure.
- Evidence must be visibly connected to the document segment it came from.

## Information architecture

### Home / upload

The landing view becomes a compact workbench instead of a split editorial hero.

- Header: Human Layer wordmark, short product claim, and supported file types.
- Main card: a clear document drop zone, selected-file summary, one primary `Analyze document` action, and progress/error feedback.
- Supporting strip: three concise promises: source traceability, decision gaps, and actionable outputs.
- The page should fit as a composed task surface on desktop and stack cleanly on narrow screens.

### Analysis result

The document result becomes a three-region decision workspace:

1. **Decision summary** — document score, quality metrics, and missing inputs; this makes readiness legible at first glance.
2. **Evidence ledger** — semantic slots with source-segment identifiers and excerpt text; each item reads as an auditable claim, not generic analysis prose.
3. **Output modes** — clean version, executive brief, and action sheet, selectable as tabs/segmented controls. The active output presents its provenance and render metadata.

On wide screens, decision summary is a narrow persistent rail and the evidence/output workspace is the main area. On mobile, these regions become a deliberate vertical sequence.

## Visual tokens

| Role | Value | Usage |
| --- | --- | --- |
| Canvas | `#F6F7F8` | application background |
| Surface | `#FFFFFF` | cards and panels |
| Ink | `#17212B` | primary text and filled action |
| Muted | `#64707D` | metadata and helper copy |
| Hairline | `#E2E7EB` | dividers and input borders |
| Signal | `#0F766E` | one primary action and active state |
| Warning | `#B45309` | decision-gap emphasis |
| Error | `#B42318` | failed upload or analysis |

Typography uses `system-ui` plus Korean fallbacks such as `Pretendard`, `Apple SD Gothic Neo`, and `Noto Sans KR`; mono is reserved for document IDs, labels, and source references. Headings are compact and functional rather than expressive display copy.

## Interaction and accessibility

- Preserve the semantic label + file input, keyboard focus, skip link, `aria-live` upload status, and error alert.
- Prevent repeat submits while upload/analysis is in flight.
- Treat the one primary button as the only filled accent on the upload page.
- Use color together with text/icon labels for readiness, warning, and error states.
- Respect `prefers-reduced-motion`; transitions stay short and non-essential.

## Data and API boundaries

The redesign consumes the existing upload, analysis, diagnosis, semantic-map, render, and output APIs. It introduces no backend behavior change. The browser still requires `NEXT_PUBLIC_API_BASE_URL` in production and the FastAPI deployment must allow the dashboard origin through `HUMAN_LAYER_CORS_ORIGINS`.

## Acceptance criteria

- Home is recognizably a focused document-analysis workbench, with no oversized decorative editorial headline or offset black shadow.
- A successful upload still moves to `/documents/:id`; failure and busy states remain clear and accessible.
- Results make score, gaps, evidence/source IDs, and generated output modes legible without adding an API dependency.
- Layout remains usable from 320px through desktop widths.
- Existing frontend tests continue to pass; new tests cover the result output selector and source-reference display.

