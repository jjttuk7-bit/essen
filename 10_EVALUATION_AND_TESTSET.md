# 10. Evaluation & Test Set

## 1. 평가 철학
좋은 결과는 단순히 더 짧은 결과가 아니다.
사람이 핵심을 더 빨리 이해하고 실제 판단에 사용할 수 있어야 한다.

## 2. Golden Set 구조
각 샘플에 다음을 저장한다.

- original_document
- human_selected_core
- human_removed_segments
- remove_reason
- human_semantic_slots
- missing_elements
- human_final_document

## 3. 편집 행동 라벨
- KEEP
- REMOVE_REDUNDANT
- REMOVE_GENERIC
- REMOVE_RHETORICAL
- MOVE_TO_APPENDIX
- MERGE
- REWRITE
- FLAG_UNSUPPORTED
- FLAG_MISSING

## 4. 핵심 평가 지표

### Extraction Recall
사람이 지정한 핵심 Signal 중 시스템이 추출한 비율

### Precision of Removal
시스템 제거 후보 중 사람이 제거에 동의한 비율

### Slot Accuracy
의미 슬롯 라벨 정확도

### Gap Detection Accuracy
사람이 중요하다고 본 누락 요소 탐지율

### Human Utility Score
1~5점:
- 이해하기 쉬움
- 핵심 파악 속도
- 판단에 도움
- 실행 가능성
- 신뢰감

## 5. 초기 테스트셋 권장
30~50개 문서
- 시장조사 10
- 기획안 10
- 전략보고 10
- 분석보고 10
- 기타 10

문서당 AI 원본과 사람이 직접 편집한 버전 모두 확보한다.
