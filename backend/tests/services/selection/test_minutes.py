"""Meeting minutes: the clearest case of a core buried in a document.

What a reader needs from minutes is small and fixed — what was decided, who owns it, by
when — and it sits inside a transcript of everything that was said. What they also need,
and never get, is the list of agenda items that produced no decision and no owner: those
are the ones that come back next week.
"""

from types import SimpleNamespace

from app.services.renderer.outline import build_outline
from app.services.selection.bottleneck import Bottleneck, detect_bottlenecks
from app.services.selection.identity import identify_document
from app.services.selection.rules import Shape, score_passage

MINUTES = [
    "2026년 3월 12일(목) 14:00–15:30\n장소: 본관 3층 회의실\n참석: 김민수(기획), 이서연(개발), 박지훈(디자인)",
    "안건 1. 공공데이터 포털 개편 일정",
    "이서연: 현재 API 연동이 지연되고 있습니다. 외부 기관 응답이 늦어서요.",
    "김민수: 그럼 오픈 일정을 조정해야 하나요?",
    "논의 결과 오픈일을 4월 15일로 2주 연기하기로 결정했다. 담당: 김민수, 기한: 3월 20일까지 관계 부서에 통보한다.",
    "안건 2. 디자인 시안 검토",
    "박지훈: 시안 3개를 준비했습니다. 각각 톤이 다릅니다.",
    "여러 의견이 오갔으나 결론을 내지 못했다. 다음 회의에서 다시 논의한다.",
    "안건 3. 예산 집행 현황",
    "이번 분기 집행률은 62%다. 별다른 이슈 없음.",
]


def _segments(texts=MINUTES) -> list[SimpleNamespace]:
    return [SimpleNamespace(id=f"segment-{index}", order_index=index, text=text) for index, text in enumerate(texts)]


class TestRecognisingMinutes:
    def test_minutes_are_recognized_by_their_header_and_agenda(self) -> None:
        assert identify_document(_segments()).kind == "회의록"

    def test_a_playbook_is_not_mistaken_for_minutes(self) -> None:
        guide = ["새 데이터를 받으면 아래 항목부터 확인한다. 이 확인 없이 다음 단계로 넘어가지 않는다.",
                 "결합 직후에는 항상 행 수를 로그로 남긴다. 반드시 기준연도를 확인한다."]

        assert identify_document(_segments(guide)).kind != "회의록"

    def test_a_transcript_without_agenda_or_attendees_is_not_minutes(self) -> None:
        plain = ["봄이 오면 마당의 나무에 새순이 돋는다.", "그 나무는 할아버지가 심었다고 한다."]

        assert identify_document(_segments(plain)).kind != "회의록"


class TestAgendaBecomesTheOutline:
    def test_agenda_items_are_read_as_headings(self) -> None:
        outline = build_outline(_segments())

        assert outline.ordered_headings[:3] == ["안건 1. 공공데이터 포털 개편 일정", "안건 2. 디자인 시안 검토", "안건 3. 예산 집행 현황"]

    def test_discussion_is_filed_under_its_agenda_item(self) -> None:
        outline = build_outline(_segments())

        assert outline.heading_for("segment-4") == "안건 1. 공공데이터 포털 개편 일정"


class TestWhatMattersInMinutes:
    def test_a_decision_outscores_the_discussion_that_produced_it(self) -> None:
        decision = score_passage("논의 결과 오픈일을 4월 15일로 2주 연기하기로 결정했다.", Shape.BODY)
        chatter = score_passage("이서연: 현재 API 연동이 지연되고 있습니다. 외부 기관 응답이 늦어서요.", Shape.BODY)

        assert decision.score > chatter.score
        assert "결정·합의" in decision.reasons

    def test_an_owner_and_a_deadline_are_recognized(self) -> None:
        result = score_passage("담당: 김민수, 기한: 3월 20일까지 관계 부서에 통보한다.", Shape.BODY)

        assert "담당·기한" in result.reasons

    def test_attributed_chatter_is_pushed_down(self) -> None:
        result = score_passage("박지훈: 시안 3개를 준비했습니다. 각각 톤이 다릅니다.", Shape.BODY)

        assert "발언 기록" in result.reasons
        assert result.score < score_passage("오픈일을 2주 연기하기로 결정했다.", Shape.BODY).score


class TestBottlenecksParticularToMinutes:
    def test_an_agenda_item_that_decided_nothing_is_reported(self) -> None:
        findings = detect_bottlenecks(_segments(), kind="회의록")

        finding = next(item for item in findings if item.kind is Bottleneck.UNDECIDED)
        assert "안건 2" in finding.detail

    def test_a_decision_without_an_owner_is_reported(self) -> None:
        undirected = MINUTES[:5] + ["안건 4. 서버 증설", "증설하기로 결정했다."]

        findings = detect_bottlenecks(_segments(undirected), kind="회의록")

        assert Bottleneck.UNASSIGNED in {finding.kind for finding in findings}

    def test_minutes_that_decided_and_assigned_everything_report_neither(self) -> None:
        clean = [MINUTES[0], MINUTES[1], MINUTES[4]]

        kinds = {finding.kind for finding in detect_bottlenecks(_segments(clean), kind="회의록")}

        assert Bottleneck.UNDECIDED not in kinds
        assert Bottleneck.UNASSIGNED not in kinds

    def test_these_bottlenecks_are_not_applied_to_other_documents(self) -> None:
        """An agenda item is a minutes concept; a playbook section decides nothing by design."""
        kinds = {finding.kind for finding in detect_bottlenecks(_segments(), kind="절차 안내서")}

        assert Bottleneck.UNDECIDED not in kinds
        assert Bottleneck.UNASSIGNED not in kinds
