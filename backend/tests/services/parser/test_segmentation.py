"""Splitting a page into paragraphs when the page has no blank lines.

Plenty of PDFs arrive with no blank line anywhere, and splitting on blank lines alone
then makes the whole page one segment. Everything downstream reads structure off
segments — headings, tables, repetition, what is buried inside a long block — so a
document that arrives as two segments cannot be condensed at all.
"""

from app.services.parser.base import segments_for_text

MINUTES_PAGE = """20 대 여성을 위한 기초 스킨케어 신제품 개발 회의록
회의 일시 2026 년 8 월 14 일(금) 14:00~15:30
회의 장소 본사 4 층 Project Room B
1. 회의 목적
20 대 여성 타깃 기초 스킨케어 라인의 1 차 제품 콘셉트를 확정한다.
• 초기 출시 범위는 토너·세럼·크림 3 종으로 확정한다.
• 클렌저와 선케어는 2 차 확장 품목으로 보류한다.
A-01 박지민 / R&D 1 차 베이스 처방 제작 2026.09.04"""


class TestPagesWithoutBlankLines:
    def test_a_page_of_unbroken_lines_is_split(self) -> None:
        segments = segments_for_text(MINUTES_PAGE)

        assert len(segments) > 1

    def test_a_bulleted_line_starts_its_own_segment(self) -> None:
        texts = [segment.text for segment in segments_for_text(MINUTES_PAGE)]

        assert "• 초기 출시 범위는 토너·세럼·크림 3 종으로 확정한다." in texts
        assert "• 클렌저와 선케어는 2 차 확장 품목으로 보류한다." in texts

    def test_a_numbered_heading_starts_its_own_segment(self) -> None:
        assert "1. 회의 목적" in [segment.text for segment in segments_for_text(MINUTES_PAGE)]

    def test_a_wrapped_sentence_stays_in_one_segment(self) -> None:
        """A line that does not close its sentence is a wrap, not a new paragraph."""
        wrapped = "\n".join([
            "신제품은 복잡한 루틴보다 매일 부담 없이 지키는",
            "3 단계 기본 관리를 핵심 가치로 설정한다.",
            "가격은 세트가 69,000 원 이하를 목표로 한다.",
            "다음 회의는 9 월 7 일에 연다.",
            "장소는 추후 공지한다.",
        ])

        texts = [segment.text for segment in segments_for_text(wrapped)]

        assert texts[0] == "신제품은 복잡한 루틴보다 매일 부담 없이 지키는 3 단계 기본 관리를 핵심 가치로 설정한다."

    def test_segments_are_numbered_in_order(self) -> None:
        segments = segments_for_text(MINUTES_PAGE)

        assert [segment.order_index for segment in segments] == list(range(len(segments)))


class TestLeavingWellFormedTextAlone:
    def test_blank_line_paragraphs_are_untouched(self) -> None:
        text = "첫 문단입니다.\n둘째 줄입니다.\n\n다른 문단입니다."

        assert [segment.text for segment in segments_for_text(text)] == ["첫 문단입니다.\n둘째 줄입니다.", "다른 문단입니다."]

    def test_a_short_unbroken_block_is_left_whole(self) -> None:
        """A few lines with no blank line is a paragraph, not a page that lost its breaks."""
        text = "제목 줄\n이어지는 설명 한 줄."

        assert len(segments_for_text(text)) == 1

    def test_a_single_line_is_one_segment(self) -> None:
        assert len(segments_for_text("한 줄뿐인 문서입니다.")) == 1

    def test_empty_text_yields_nothing(self) -> None:
        assert segments_for_text("   \n  \n") == []


class TestOnlyFullLinesWrap:
    """A line that stopped short of the column width ended because its content ended."""

    HEADER = "\n".join([
        "20 대 여성을 위한 기초 스킨케어 신제품 개발 회의록",
        "회의 일시 2026 년 8 월 14 일(금) 14:00~15:30",
        "회의 장소 본사 4 층 Project Room B",
        "작성자 김서현",
        "회의 목적 20 대 여성 타깃 기초 스킨케어 라인의 1 차 제품 콘셉트 및 개발 방",
        "향 확정",
        "참석자 김서현(상품기획), 박지민(R&D), 이나영(마케팅), 최유진(디자인), 정",
        "민호(영업), 한소라(QA)",
    ])

    def test_short_header_lines_stay_separate(self) -> None:
        texts = [segment.text for segment in segments_for_text(self.HEADER)]

        assert "회의 장소 본사 4 층 Project Room B" in texts
        assert "작성자 김서현" in texts

    def test_a_full_line_continues_onto_the_next(self) -> None:
        texts = [segment.text for segment in segments_for_text(self.HEADER)]

        assert any(text.endswith("개발 방향 확정") for text in texts), texts

    def test_a_korean_wrap_does_not_gain_a_space_mid_word(self) -> None:
        """Korean lines break anywhere, so the break is usually inside a word."""
        texts = [segment.text for segment in segments_for_text(self.HEADER)]

        assert not any("방 향" in text for text in texts)
        assert any("정민호(영업)" in text for text in texts)

    def test_a_latin_wrap_keeps_its_word_boundary(self) -> None:
        wrapped = "\n".join([
            "The quarterly review covers every regional office and the results are",
            "summarised below.",
            "Attendance was lower than in either of the two preceding quarters.",
            "Every office submitted its figures ahead of the stated deadline.",
        ])

        assert "results are summarised below." in segments_for_text(wrapped)[0].text


class TestOnlyWrappedProseNeedsRecovering:
    """Short lines are already one item each; re-splitting them by column width is noise."""

    LIST_PAGE = "\n".join(["완전성", "일관성", "정확성", "유효성", "적시성", "① 결측은 어떻게 표기되어 있는가?", "② 한 행은 무엇인가?"])

    def test_a_block_of_short_lines_is_left_whole(self) -> None:
        assert len(segments_for_text(self.LIST_PAGE)) == 1

    def test_a_block_of_full_prose_lines_is_recovered(self) -> None:
        prose = "\n".join([
            "20 대 여성 타깃 기초 스킨케어 라인의 1 차 제품 콘셉트 및 개발 방향을 확정한다.",
            "회의 장소 본사 4 층 Project Room B",
            "핵심 타깃은 20~29 세 여성이며 대학생과 사회초년생 비중이 높은 것으로 가정한다.",
            "작성자 김서현",
        ])

        assert len(segments_for_text(prose)) > 1
