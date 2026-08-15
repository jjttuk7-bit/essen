# 03. Document Semantic Standard v0.1

## 1. 목적
모든 문서를 형식으로 분류하기 전에 의미 슬롯으로 구조화한다.

핵심 원칙:
Meaning → Structure → Format

## 2. 기본 10개 슬롯

| Slot | 의미 | 필수성 |
|---|---|---|
| PURPOSE | 문서가 존재하는 이유 | 필수 |
| AUDIENCE | 읽는 사람 | 필수 |
| CONTEXT | 상황과 배경 | 선택 |
| PROBLEM | 해결/판단 대상 문제 | 필수 |
| FACT | 확인된 사실 | 선택 |
| EVIDENCE | 사실/주장의 근거 | 선택 |
| INTERPRETATION | 사실에 대한 해석 | 선택 |
| DECISION | 결정해야 할 것 | 목적에 따라 필수 |
| ACTION | 실행해야 할 것 | 목적에 따라 필수 |
| RISK_UNKNOWN | 위험, 가정, 미확인 요소 | 선택 |

## 3. 확장 슬롯
실제 구현에서는 아래 슬롯을 추가한다.

- CLAIM: 문서 내 핵심 주장
- OPTION: 가능한 대안
- TRADE_OFF: 대안 간 장단점/비용
- RECOMMENDATION: 작성자의 권고
- OWNER: 실행 책임자
- DEADLINE: 실행 기한
- PRIORITY: 우선순위
- SUCCESS_CRITERIA: 완료/성공 기준
- SOURCE: 근거 출처
- CONFIDENCE: 정보 신뢰도

## 4. 3계층 구조

### Level A — Document Level
- PURPOSE
- AUDIENCE
- DOCUMENT_TYPE
- CONTEXT

### Level B — Reasoning Level
- PROBLEM
- CLAIM
- FACT
- EVIDENCE
- INTERPRETATION
- OPTION
- TRADE_OFF
- RECOMMENDATION
- DECISION
- RISK_UNKNOWN

### Level C — Execution Level
- ACTION
- OWNER
- DEADLINE
- PRIORITY
- SUCCESS_CRITERIA

## 5. 문서 목적 분류
초기 버전은 7종으로 제한한다.

- INFORM
- EXPLAIN
- DECIDE
- PERSUADE
- PLAN
- EXECUTE
- RECORD

## 6. 슬롯 객체 예시
```json
{
  "slot": "DECISION",
  "text": "3개월 유료 PoC를 진행할지 결정해야 한다.",
  "source_span": [1204, 1266],
  "confidence": 0.94,
  "importance": 0.96,
  "evidence_links": ["evi_03", "evi_07"]
}
```

## 7. 슬롯 간 관계
- FACT -> supported_by -> EVIDENCE
- CLAIM -> supported_by -> EVIDENCE
- FACT -> interpreted_as -> INTERPRETATION
- PROBLEM -> has_option -> OPTION
- OPTION -> has_tradeoff -> TRADE_OFF
- RECOMMENDATION -> resolves -> PROBLEM
- DECISION -> triggers -> ACTION
- ACTION -> owned_by -> OWNER
- ACTION -> due_at -> DEADLINE
- ACTION -> measured_by -> SUCCESS_CRITERIA

## 8. 필수 검증 규칙 예시
DECIDE 문서:
- PROBLEM 필수
- 최소 1개 OPTION 권장
- EVIDENCE 없으면 경고
- DECISION 또는 RECOMMENDATION 없으면 경고
- ACTION 없으면 '의사결정 후속조치 미정' 표시

PLAN 문서:
- PURPOSE, ACTION, OWNER 권장
- DEADLINE 미존재 시 경고
- SUCCESS_CRITERIA 미존재 시 경고
