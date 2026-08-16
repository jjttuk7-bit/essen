"""The rule layer decides what is core without calling a model.

It exists for two reasons: selection must be reproducible, and the reader is owed a
concrete reason a passage was dropped. A model score explains nothing; a rule can say
"일반론 표현" or "목차 항목". Sentences below are taken from a real source document.
"""

import pytest

from app.services.selection.rules import Shape, classify_shape, score_passage

TOC = """목차
서문 왜 “사고 흐름”이 핵심인가
PART 1 전체 사고 흐름 10단계
PART 2 공공데이터를 처음 받았을 때
PART 3 “한 행은 무엇인가?”
PART 4 메타데이터 → 프로파일링 → 품질진단"""

TABLE = """축
진단 질문
흔한 문제 유형
일관성
정확성
유효성
적시성"""

CHECKLIST = "① 이 데이터는 어떤 문제의식에서 왜 필요한가?"

BODY = "새 데이터를 받으면 파일을 열기 전에, 또는 연 직후 10분 안에 아래 항목부터 확인한다."


class TestShape:
    def test_a_table_of_contents_is_recognized(self) -> None:
        assert classify_shape(TOC) is Shape.TOC

    def test_a_table_fragment_is_recognized(self) -> None:
        assert classify_shape(TABLE) is Shape.TABLE

    def test_a_checklist_item_is_recognized(self) -> None:
        assert classify_shape(CHECKLIST) is Shape.CHECKLIST

    def test_ordinary_prose_is_body(self) -> None:
        assert classify_shape(BODY) is Shape.BODY


class TestProposition:
    @pytest.mark.parametrize("passage", [
        "이 확인 없이 다음 단계로 넘어가지 않는다.",
        "정책 효과를 주장하려면 원인분석 단계의 절차를 반드시 거쳐야 한다.",
        "결합 직후에는 항상 결합 전 행 수와 결합 후 행 수를 로그로 남긴다.",
    ])
    def test_a_directive_scores_above_a_neutral_statement(self, passage: str) -> None:
        assert score_passage(passage, Shape.BODY).score > score_passage("이 문서는 열세 개의 부로 이루어져 있다.", Shape.BODY).score

    def test_a_directive_is_named_in_the_reasons(self) -> None:
        assert "실행 지시" in score_passage("이 확인 없이 다음 단계로 넘어가지 않는다.", Shape.BODY).reasons

    def test_a_warning_is_recognized(self) -> None:
        result = score_passage("상관관계와 인과관계를 혼동하는 것이 가장 흔한 오류다.", Shape.BODY)

        assert "주의·위험" in result.reasons


class TestDensity:
    def test_a_passage_carrying_figures_outscores_the_same_claim_without_them(self) -> None:
        with_figures = score_passage("A동은 다른 동 대비 도보 10분 내 체육시설 접근률이 32%p 낮다.", Shape.BODY)
        without = score_passage("A동은 다른 동 대비 체육시설 접근률이 낮다.", Shape.BODY)

        assert with_figures.score > without.score
        assert "수치 근거" in with_figures.reasons

    @pytest.mark.parametrize("passage", [
        "일반적으로 데이터 품질은 매우 중요하다.",
        "다양한 방법을 통해 바람직한 결과를 얻을 수 있다.",
    ])
    def test_boilerplate_generalities_are_pushed_down(self, passage: str) -> None:
        result = score_passage(passage, Shape.BODY)

        assert "일반론 표현" in result.reasons
        assert result.score < score_passage(BODY, Shape.BODY).score


class TestShapeAffectsScore:
    def test_a_table_of_contents_line_scores_near_zero(self) -> None:
        assert score_passage("PART 4 메타데이터 → 프로파일링 → 품질진단", Shape.TOC).score < 0.15

    def test_the_shape_reason_is_reported(self) -> None:
        assert "목차 항목" in score_passage("PART 4 메타데이터", Shape.TOC).reasons
        assert "표 조각" in score_passage("일관성", Shape.TABLE).reasons

    def test_a_checklist_item_is_not_penalised_like_furniture(self) -> None:
        """Checklist lines are the actionable core of some documents, not page furniture."""
        assert score_passage("파일 형식·인코딩을 확인했다", Shape.CHECKLIST).score > score_passage("일관성", Shape.TABLE).score


class TestContract:
    @pytest.mark.parametrize("passage", ["", "   ", BODY, TOC, CHECKLIST])
    @pytest.mark.parametrize("shape", list(Shape))
    def test_the_score_always_stays_within_range(self, passage: str, shape: Shape) -> None:
        assert 0.0 <= score_passage(passage, shape).score <= 1.0

    def test_every_score_carries_at_least_one_reason(self) -> None:
        assert score_passage(BODY, Shape.BODY).reasons

    def test_scoring_is_reproducible(self) -> None:
        assert score_passage(BODY, Shape.BODY) == score_passage(BODY, Shape.BODY)
