# 04. Processing Pipeline

## 전체 흐름

Input Document
→ Parse
→ Segment
→ Purpose/Audience Classification
→ Semantic Slot Extraction
→ Signal/Noise Classification
→ Redundancy Clustering
→ Evidence/Gap Analysis
→ Importance Ranking
→ Reasoning Reconstruction
→ Human-ready Rendering
→ Quality Check

## 1. Input Parse
지원 우선순위:
1. TXT/Markdown
2. DOCX
3. PDF
4. PPTX

MVP에서는 TXT/Markdown/PDF text extraction부터 시작해도 된다.

## 2. Segmentation
문서를 문단/문장 단위로 나누고 각 segment에 ID 부여.

```json
{
  "segment_id": "seg_0012",
  "text": "...",
  "page": 3,
  "paragraph": 5
}
```

## 3. Purpose & Audience
LLM 분류 + 규칙 검증.

출력:
- purpose
- probable_audience
- confidence
- rationale_short

## 4. Semantic Extraction
각 segment를 하나 이상의 slot에 매핑.
하나의 문장이 FACT + INTERPRETATION을 동시에 포함할 수 있으므로 multi-label 허용.

## 5. Signal / Noise Classification
각 segment에 다음 레이블 부여.

- CORE_SIGNAL
- SUPPORTING_SIGNAL
- CONTEXT
- REDUNDANT
- GENERIC
- RHETORICAL
- UNSUPPORTED
- OFF_PURPOSE

## 6. Redundancy Clustering
의미적으로 동일한 문장들을 하나의 cluster로 묶는다.
대표 문장만 남기고 나머지는 제거 후보로 표시.

## 7. Gap Analysis
문서 목적에 따라 필요한 슬롯 대비 빠진 슬롯을 탐지.

예:
DECIDE 문서인데 OPTION, EVIDENCE, TRADE_OFF, DECISION이 없으면 gap 생성.

## 8. Importance Ranking
각 segment/slot에 0~1 중요도 부여.

기본 요소:
- 목적 직접 관련성
- 결정 영향도
- 근거 존재 여부
- 새 정보량
- 반복 여부
- 독자 관련성

## 9. Reasoning Reconstruction
문서의 논리를 다음 구조 중 하나로 재구성.

Decision:
Situation → Problem → Options → Evidence → Trade-off → Recommendation → Decision → Action

Analysis:
Question → Data → Findings → Interpretation → Implication

Plan:
Goal → Current State → Gap → Tasks → Owner → Timeline → Risk → Success Criteria

## 10. Rendering
사용자 선택 출력:
- Clean Version
- Executive 1-page
- Decision Memo
- Action Plan
- Email Brief
- Presentation Outline

MVP 기본 출력은 3개:
1. Clean Version
2. Executive Summary
3. Action & Decision Sheet
