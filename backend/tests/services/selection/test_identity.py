"""Say what the document is before saying what it contains.

A reader handed a condensed document still has to work out what they are holding — a
procedure guide, a findings report, a set of minutes — and that work comes before any of
the content is usable. The identity is measured from the document or quoted from it;
nothing here describes a document in words the document did not use.
"""

from types import SimpleNamespace

from app.services.selection.identity import identify_document


def _segment(index: int, text: str) -> SimpleNamespace:
    return SimpleNamespace(id=f"segment-{index}", order_index=index, text=text)


GUIDE = [
    _segment(0, "공공데이터 분석·처리·설계 실전 플레이북"),
    _segment(1, "이 플레이북이 채우려는 빈자리는 다른 곳에 있다 — 공공데이터를 받아 든 사람이 그 다음에 무엇을 어떤 순서로 생각해야 하는가이다."),
    _segment(2, "새 데이터를 받으면 파일을 열기 전에 아래 항목부터 확인한다. 이 확인 없이 다음 단계로 넘어가지 않는다."),
    _segment(3, "결합 직후에는 항상 결합 전 행 수를 로그로 남긴다. 반드시 기준연도 컬럼을 확인한다."),
]

REPORT = [
    _segment(0, "2025년 상반기 공공체육시설 이용 현황 보고"),
    _segment(1, "A동은 다른 동 대비 도보 10분 내 접근률이 32%p 낮다. 이용자는 전년 대비 12% 감소했다."),
    _segment(2, "결측·오류 시설은 전체의 6% 수준으로 나타났다. 따라서 A동 우선 투자가 필요하다."),
]


class TestWhatKindOfDocument:
    def test_a_procedure_guide_is_recognized(self) -> None:
        assert identify_document(GUIDE).kind == "절차 안내서"

    def test_a_findings_report_is_recognized(self) -> None:
        assert identify_document(REPORT).kind == "분석 보고서"

    def test_an_unfamiliar_document_gets_a_neutral_kind(self) -> None:
        plain = [_segment(0, "봄이 오면 마당의 나무에 새순이 돋는다."), _segment(1, "그 나무는 할아버지가 심었다고 한다.")]

        assert identify_document(plain).kind == "일반 문서"


class TestScale:
    def test_the_reader_is_told_how_much_document_there_is(self) -> None:
        identity = identify_document(GUIDE)

        assert identity.segment_count == 4
        assert identity.character_count == sum(len(segment.text) for segment in GUIDE)

    def test_sections_are_counted_from_the_source_headings(self) -> None:
        sectioned = [_segment(0, "PART 1 개요\n본문이 이어진다."), _segment(1, "PART 2 절차\n본문이 이어진다."), _segment(2, "맺음말\n마무리한다.")]

        assert identify_document(sectioned).section_count == 3


class TestPurpose:
    def test_the_document_s_own_statement_of_purpose_is_quoted(self) -> None:
        purpose = identify_document(GUIDE).purpose

        assert purpose is not None
        assert purpose in GUIDE[1].text

    def test_the_purpose_is_never_written_for_the_document(self) -> None:
        source = " ".join(segment.text for segment in REPORT)
        purpose = identify_document(REPORT).purpose

        assert purpose is None or purpose in source

    def test_a_document_that_never_states_its_purpose_reports_none(self) -> None:
        plain = [_segment(0, "봄이 오면 마당의 나무에 새순이 돋는다.")]

        assert identify_document(plain).purpose is None


class TestContract:
    def test_an_empty_document_is_still_describable(self) -> None:
        identity = identify_document([])

        assert identity.segment_count == 0
        assert identity.kind

    def test_identification_is_reproducible(self) -> None:
        assert identify_document(GUIDE) == identify_document(GUIDE)


class TestKindsFoundInRealDocuments:
    """Thresholds were guesses until a real document was measured against them."""

    def test_a_guide_organized_around_questions_is_still_a_guide(self) -> None:
        """The source playbook asks more questions than it issues instructions."""
        segments = [_segment(index, "한 행은 정확히 무엇을 의미하는가?") for index in range(8)]
        segments += [_segment(index + 8, "이 확인 없이 다음 단계로 넘어가지 않는다. 반드시 기준연도 컬럼을 확인한다.") for index in range(4)]

        assert identify_document(segments).kind == "절차 안내서"

    def test_a_document_that_only_asks_is_a_questionnaire(self) -> None:
        segments = [_segment(index, f"{index}. 이 데이터는 어떤 문제의식에서 왜 필요한가?") for index in range(10)]

        assert identify_document(segments).kind == "질문지"

    def test_table_cells_do_not_decide_the_kind(self) -> None:
        """Flattened tables carry incidental question marks; only prose should count."""
        table = _segment(0, "1 문제정의 무엇을 알고 싶은가? 2 데이터 이해 한 행은? 3 품질진단 믿고 써도 되는가? 4 탐색 어떤 모습인가? 5 원인 왜인가?")
        prose = [_segment(index + 1, "결합 직후에는 항상 행 수를 로그로 남긴다. 반드시 확인한다.") for index in range(3)]

        assert identify_document([table, *prose]).kind == "절차 안내서"


class TestPurposeSpanningTwoSentences:
    def test_a_purpose_continued_after_a_dash_is_quoted_whole(self) -> None:
        segments = [_segment(0, '이 문서가 채우려는 빈자리는 다른 곳에 있다. — "공공데이터를 받아 든 사람이 그 다음에 무엇을 생각해야 하는가"이다.')]

        purpose = identify_document(segments).purpose

        assert purpose is not None
        assert "공공데이터를 받아 든 사람이" in purpose
        assert purpose in " ".join(segments[0].text.split())
