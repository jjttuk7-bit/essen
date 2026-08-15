# 07. Data Model & API

## 1. 권장 기술 스택
MVP:
- Backend: FastAPI
- Frontend: Next.js 또는 Streamlit
- DB: SQLite -> PostgreSQL
- LLM Adapter: provider abstraction
- Embedding: 선택적 사용

## 2. 핵심 데이터 모델

### Document
- id
- title
- source_type
- raw_text
- purpose
- audience
- created_at

### Segment
- id
- document_id
- order_index
- text
- page
- token_count

### SemanticSlot
- id
- segment_id
- slot_type
- normalized_text
- confidence
- importance

### Relation
- from_slot_id
- relation_type
- to_slot_id

### QualityLabel
- segment_id
- label
- score
- reason

### Gap
- document_id
- gap_type
- severity
- description

### RenderedOutput
- document_id
- output_type
- content
- version

## 3. API 예시

POST /documents
- 문서 업로드

POST /documents/{id}/analyze
- 전체 분석 실행

GET /documents/{id}/diagnosis
- 품질/Signal/Gap 결과

GET /documents/{id}/semantic-map
- 슬롯/관계 조회

POST /documents/{id}/render
```json
{
  "output_type": "executive_summary",
  "audience": "CEO",
  "max_words": 800
}
```

GET /documents/{id}/outputs

## 4. 분석 결과 JSON 예시
```json
{
  "document_id": "doc_001",
  "purpose": "DECIDE",
  "signal_ratio": 0.34,
  "redundancy_ratio": 0.22,
  "generic_ratio": 0.18,
  "evidence_coverage": 0.41,
  "decision_completeness": 0.52,
  "gaps": [
    "고객 수요 데이터 없음",
    "대안 비교 없음",
    "의사결정 기준 없음"
  ]
}
```
