"""What in this document costs the reader time.

The product's claim is not that a document is long but that parts of it waste the reader's
attention: structure they must read to discover is not content, the same point again,
sentences that say nothing specific, and a decision buried inside a wall of prose. Naming
those is what turns "원문의 26%입니다" into a reason the reader can act on.
"""

from types import SimpleNamespace

from app.services.selection.bottleneck import Bottleneck, detect_bottlenecks


def _segment(index: int, text: str) -> SimpleNamespace:
    return SimpleNamespace(id=f"segment-{index}", order_index=index, text=text)


def _kinds(findings) -> set[Bottleneck]:
    return {finding.kind for finding in findings}


def _finding(findings, kind: Bottleneck):
    return next(finding for finding in findings if finding.kind is kind)


PROSE = "새 데이터를 받으면 파일을 열기 전에 아래 항목부터 확인한다."
TOC = "목차\nPART 1 개요\nPART 2 절차\nPART 3 검증\nPART 4 정리"
TABLE = "축\n진단 질문\n흔한 문제\n일관성\n정확성\n유효성"


class TestStructureNoise:
    def test_a_table_of_contents_and_a_flattened_table_are_noise(self) -> None:
        findings = detect_bottlenecks([_segment(0, TOC), _segment(1, TABLE), _segment(2, PROSE)])

        assert Bottleneck.STRUCTURE_NOISE in _kinds(findings)
        assert _finding(findings, Bottleneck.STRUCTURE_NOISE).segment_ids == ("segment-0", "segment-1")

    def test_the_share_reflects_how_much_of_the_document_it_is(self) -> None:
        findings = detect_bottlenecks([_segment(0, TOC), _segment(1, PROSE)])

        assert _finding(findings, Bottleneck.STRUCTURE_NOISE).share == 0.5

    def test_prose_alone_reports_no_structure_noise(self) -> None:
        assert Bottleneck.STRUCTURE_NOISE not in _kinds(detect_bottlenecks([_segment(0, PROSE)]))


class TestRepetition:
    def test_a_restated_paragraph_is_repetition(self) -> None:
        original = "결합 직후에는 결합 전 행 수와 결합 후 행 수를 로그로 남긴다."
        restated = "결합 직후에는 결합 전 행 수와 결합 후의 행 수를 반드시 로그로 남긴다."

        findings = detect_bottlenecks([_segment(0, original), _segment(1, restated)])

        assert Bottleneck.REPETITION in _kinds(findings)
        assert _finding(findings, Bottleneck.REPETITION).segment_ids == ("segment-1",)

    def test_the_first_statement_is_not_the_repeat(self) -> None:
        text = "같은 문장을 그대로 반복한다."
        findings = detect_bottlenecks([_segment(0, text), _segment(1, text), _segment(2, text)])

        assert _finding(findings, Bottleneck.REPETITION).segment_ids == ("segment-1", "segment-2")

    def test_different_paragraphs_are_not_repetition(self) -> None:
        findings = detect_bottlenecks([_segment(0, PROSE), _segment(1, "품질진단 5축은 완전성과 일관성을 포함한다.")])

        assert Bottleneck.REPETITION not in _kinds(findings)


class TestGenerality:
    def test_a_passage_that_says_nothing_specific_is_named(self) -> None:
        findings = detect_bottlenecks([_segment(0, "일반적으로 데이터 품질은 매우 중요하다."), _segment(1, PROSE)])

        assert Bottleneck.GENERALITY in _kinds(findings)
        assert _finding(findings, Bottleneck.GENERALITY).segment_ids == ("segment-0",)


class TestBuriedCore:
    def test_a_decision_inside_a_wall_of_prose_is_reported(self) -> None:
        filler = "이 절에서는 배경과 맥락을 차례로 설명하고 있으며 여러 사례를 들어 보충한다. " * 12
        findings = detect_bottlenecks([_segment(0, filler + " 이 확인 없이 다음 단계로 넘어가지 않는다.")])

        assert Bottleneck.BURIED_CORE in _kinds(findings)

    def test_a_short_passage_is_not_buried(self) -> None:
        findings = detect_bottlenecks([_segment(0, "이 확인 없이 다음 단계로 넘어가지 않는다.")])

        assert Bottleneck.BURIED_CORE not in _kinds(findings)

    def test_a_long_passage_with_no_core_at_all_is_not_buried_core(self) -> None:
        """Nothing is buried when there is nothing to surface."""
        filler = "이 절에서는 배경과 맥락을 차례로 설명하고 있다. " * 15

        assert Bottleneck.BURIED_CORE not in _kinds(detect_bottlenecks([_segment(0, filler)]))


class TestUnresolved:
    def test_a_run_of_open_questions_is_reported(self) -> None:
        questions = [_segment(index, f"{index}. 이 데이터는 어떤 문제의식에서 필요한가?") for index in range(4)]

        findings = detect_bottlenecks(questions + [_segment(9, PROSE)])

        assert Bottleneck.UNRESOLVED in _kinds(findings)


class TestContract:
    def test_an_empty_document_reports_nothing(self) -> None:
        assert detect_bottlenecks([]) == []

    def test_a_clean_document_reports_nothing(self) -> None:
        assert detect_bottlenecks([_segment(0, PROSE), _segment(1, "품질진단 5축은 완전성을 포함한다.")]) == []

    def test_every_finding_explains_itself_in_the_reader_s_language(self) -> None:
        findings = detect_bottlenecks([_segment(0, TOC), _segment(1, "일반적으로 매우 중요하다."), _segment(2, PROSE)])

        assert all(finding.detail for finding in findings)
        assert all(0.0 < finding.share <= 1.0 for finding in findings)

    def test_findings_are_ordered_by_how_much_they_cost(self) -> None:
        segments = [_segment(index, TOC) for index in range(4)] + [_segment(9, "일반적으로 매우 중요하다."), _segment(10, PROSE)]

        findings = detect_bottlenecks(segments)

        assert [finding.share for finding in findings] == sorted((f.share for f in findings), reverse=True)


class TestWhatCountsAsABottleneckDependsOnTheDocument:
    """A trait is only a defect relative to what the document is trying to be."""

    QUESTIONS = [_segment(index, f"{index}. 이 데이터는 어떤 문제의식에서 필요한가?") for index in range(5)]

    def test_open_questions_are_a_bottleneck_in_a_report(self) -> None:
        """A report that only asks leaves the reader unable to decide."""
        kinds = _kinds(detect_bottlenecks(self.QUESTIONS, kind="분석 보고서"))

        assert Bottleneck.UNRESOLVED in kinds

    def test_open_questions_are_the_design_of_a_guide(self) -> None:
        assert Bottleneck.UNRESOLVED not in _kinds(detect_bottlenecks(self.QUESTIONS, kind="절차 안내서"))

    def test_open_questions_are_the_whole_point_of_a_questionnaire(self) -> None:
        assert Bottleneck.UNRESOLVED not in _kinds(detect_bottlenecks(self.QUESTIONS, kind="질문지"))

    def test_minutes_report_the_undecided_agenda_rather_than_the_questions(self) -> None:
        """Both would describe the same failure; the agenda one says it usefully."""
        assert Bottleneck.UNRESOLVED not in _kinds(detect_bottlenecks(self.QUESTIONS, kind="회의록"))


class TestTablesInAReportAreTheEvidence:
    TABLE_HEAVY = [
        _segment(0, "축\n완전성\n일관성\n정확성\n유효성"),
        _segment(1, "구분\n1분기\n2분기\n3분기\n4분기"),
        _segment(2, "집행률은 62%로 계획을 밑돈다."),
    ]

    def test_a_table_is_structure_noise_in_a_guide(self) -> None:
        assert Bottleneck.STRUCTURE_NOISE in _kinds(detect_bottlenecks(self.TABLE_HEAVY, kind="절차 안내서"))

    def test_a_table_is_not_noise_in_a_report(self) -> None:
        assert Bottleneck.STRUCTURE_NOISE not in _kinds(detect_bottlenecks(self.TABLE_HEAVY, kind="분석 보고서"))

    def test_a_contents_page_is_still_noise_in_a_report(self) -> None:
        """Only tables carry a report's evidence; its contents page carries nothing."""
        segments = [_segment(0, TOC), _segment(1, "집행률은 62%로 계획을 밑돈다.")]

        assert Bottleneck.STRUCTURE_NOISE in _kinds(detect_bottlenecks(segments, kind="분석 보고서"))


class TestTheDefaultIsUnchanged:
    def test_an_unknown_kind_keeps_every_general_bottleneck(self) -> None:
        segments = [_segment(0, TOC), _segment(1, "일반적으로 매우 중요하다."), _segment(2, PROSE)]

        assert _kinds(detect_bottlenecks(segments, kind="처음 보는 종류")) == _kinds(detect_bottlenecks(segments))
