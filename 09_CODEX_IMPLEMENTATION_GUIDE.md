# 09. Codex Implementation Guide

## 1. Codex 역할
Codex는 한 번에 전체 서비스를 만들지 않는다.
작은 수직 슬라이스를 반복 구현한다.

## 2. 개발 순서

### Phase 1 — Skeleton
- FastAPI 프로젝트 생성
- 파일 업로드
- 텍스트 저장
- SQLite 모델
- 기본 분석 엔드포인트

### Phase 2 — Semantic Extraction
- 문장/문단 segmentation
- LLM adapter
- purpose classification
- semantic slot extraction
- JSON schema validation

### Phase 3 — Signal Engine
- segment classification
- redundancy detection
- simple scoring
- diagnosis endpoint

### Phase 4 — Rendering
- clean version
- executive summary
- action/decision sheet

### Phase 5 — UI
- upload
- diagnosis dashboard
- semantic slot panel
- original vs human-ready diff

## 3. 구현 원칙
- 모든 LLM 출력은 Pydantic schema로 검증
- raw LLM response 저장
- prompt version 저장
- 결정 이유(reason) 저장
- 원문 span 추적
- 변환 시 원문에 없는 사실 생성 금지
- confidence 낮은 항목은 human review 대상으로 표시

## 4. 초기 디렉터리 구조
```text
app/
  api/
  core/
  models/
  schemas/
  services/
    parser/
    llm/
    semantic/
    signal/
    renderer/
  prompts/
  tests/
  main.py
```

## 5. 첫 번째 Codex 지시문
```text
Build an MVP backend for a Document Intelligence Engine.
Use FastAPI, Pydantic, SQLAlchemy and SQLite.

Core workflow:
1. Upload a text or markdown document.
2. Segment it into paragraphs.
3. Store the raw document and segments.
4. Analyze each segment into semantic slots using a pluggable LLM adapter.
5. Classify each segment as CORE_SIGNAL, SUPPORTING_SIGNAL, CONTEXT, REDUNDANT, GENERIC, RHETORICAL, UNSUPPORTED, or OFF_PURPOSE.
6. Calculate signal_ratio, redundancy_ratio, generic_ratio and decision_completeness.
7. Return a diagnosis JSON.

Important constraints:
- Do not invent facts that are not present in the source.
- Every extracted semantic item must keep source_segment_id.
- Every model output must be validated with Pydantic.
- Store prompt_version and raw_model_output for auditability.
- Write unit tests for scoring and schema validation.
- Keep the LLM provider behind an interface so it can be replaced later.
```

## 6. 두 번째 Codex 지시문
```text
Add a rendering layer to the existing project.
Create three output modes:
- clean_version
- executive_summary
- action_decision_sheet

The renderer must use only validated semantic slots from the analysis layer.
It must not add unsupported facts.
For every rendered section, retain provenance references to source segment IDs.
Add an API endpoint POST /documents/{id}/render.
Add tests that fail if the renderer outputs a claim not linked to any source semantic slot.
```
