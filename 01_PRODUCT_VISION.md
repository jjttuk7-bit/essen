# 01. Product Vision

## 1. 제품 정의
Human Layer는 AI가 생성한 문서를 단순 요약하는 도구가 아니다.

입력:
- ChatGPT/Claude/Gemini/Copilot/Codex 등으로 생성한 문서
- 보고서, 기획안, 리서치, 회의자료, 제안서, 분석문서, 메모

출력:
- 사람이 빠르게 이해할 수 있는 핵심 정보
- 무엇이 사실이고 무엇이 주장인지 구분된 구조
- 빠진 근거와 결정 요소
- 실제 의사결정과 실행에 사용 가능한 문서

## 2. 핵심 문제
AI 생산성이 높아질수록 문서의 양은 늘지만 사람이 실제로 소비할 수 있는 정보량은 증가하지 않는다.

대표 증상:
- 문장이 길지만 실제 정보는 적다.
- 같은 의미를 여러 문장으로 반복한다.
- 관련성은 있지만 지금 필요하지 않은 내용이 많다.
- 사실, 해석, 제안, 결정이 섞여 있다.
- 결정과 실행 항목이 모호하다.
- 중요한 정보와 덜 중요한 정보의 밀도가 비슷하다.

## 3. 제품의 중심 가설
LLM은 Relevant Information Generator로 매우 강하다.
그러나 실제 업무 문서는 Necessary Information Selector가 필요하다.

따라서 제품의 핵심은:
Select → Compress → Structure → Validate → Reconstruct → Express

## 4. 핵심 가치 제안
"30페이지 AI 보고서를 상사가 3분 안에 판단할 수 있는 문서로 바꾼다."

## 5. 차별화
일반 요약기:
Document → Summary

Human Layer:
Document → Semantic Structure → Signal/Noise Analysis → Missing Decision Elements → Audience Adaptation → Human-ready Document

## 6. 핵심 제품 용어
- Human Layer: AI와 사람 사이의 정보 변환 계층
- Document Intelligence Engine: 문서의 목적, 정보 밀도, 논리 구조, 누락 요소를 분석하는 엔진
- Document Compiler: 원시 문서를 사람이 사용 가능한 문서로 컴파일하는 전체 파이프라인
- Signal: 현재 문서의 목적 달성에 필요한 실제 정보
- Noise: 중복, 수사, 일반론, 저정보 문장
- Editorial Intelligence: 무엇을 남기고, 버리고, 강조하고, 보완할지를 판단하는 능력
