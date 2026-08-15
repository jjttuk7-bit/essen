# 05. Signal & Quality Engine

## 1. 목표
문서의 길이가 아니라 실제 정보량과 의사결정 가능성을 측정한다.

## 2. 주요 지표

### 2.1 Signal Ratio
실제 유효 정보 토큰 / 전체 토큰

단순 MVP 근사:
(CORE_SIGNAL + SUPPORTING_SIGNAL 토큰) / 전체 토큰

### 2.2 Redundancy Ratio
REDUNDANT 토큰 / 전체 토큰

### 2.3 Generic Ratio
GENERIC + RHETORICAL 토큰 / 전체 토큰

### 2.4 Evidence Coverage
근거 링크가 존재하는 핵심 CLAIM 수 / 전체 핵심 CLAIM 수

### 2.5 Decision Completeness
DECIDE 문서에서 필요한 슬롯 충족률

예:
PROBLEM 20
OPTION 15
EVIDENCE 20
TRADE_OFF 15
RECOMMENDATION 15
DECISION 10
ACTION 5
총 100점

### 2.6 Actionability Score
ACTION에 OWNER/DEADLINE/SUCCESS_CRITERIA가 연결된 비율

## 3. Document Signal Score
초기 가중치 예시:

- Signal Ratio 25%
- Evidence Coverage 20%
- Decision Completeness 20%
- Actionability 15%
- Low Redundancy 10%
- Low Generic Content 10%

## 4. 정보 밀도 진단 문구
점수만 보여주지 말고 원인을 설명한다.

예:
- 핵심 문장 18개
- 반복 문장 22개
- 일반론 14개
- 근거 없는 핵심 주장 4개
- 결정 필요사항 2개
- 실행 주체 미지정 3개

## 5. 제거 규칙
삭제 후보는 자동 삭제 전 반드시 이유를 보존한다.

```json
{
  "segment_id": "seg_020",
  "decision": "REMOVE_CANDIDATE",
  "reason": "동일 의미가 seg_014에 더 구체적으로 존재함",
  "category": "REDUNDANT"
}
```

## 6. 중요한 원칙
- 짧다고 좋은 문서가 아니다.
- Evidence가 많은 문서가 항상 좋은 문서도 아니다.
- 문서 목적에 필요한 정보 밀도가 높은지가 핵심이다.
