"""The condensed document must keep the source document's own structure.

Re-filing content under an analysis taxonomy (Decision / Evidence / Context) loses the
order and logic a reader already knows, which makes the result harder to use than the
original. These tests pin the recovery of the document's own headings.
"""

from types import SimpleNamespace

from app.services.renderer.outline import build_outline

RUNNING_HEADER = "공공데이터 분석·처리·설계 실전 플레이북"


def _segment(index: int, text: str) -> SimpleNamespace:
    return SimpleNamespace(id=f"segment-{index}", order_index=index, text=text)


def _playbook() -> list[SimpleNamespace]:
    return [
        _segment(0, f"1\n{RUNNING_HEADER}\n목차\n서문 왜 “사고 흐름”이 핵심인가"),
        _segment(1, f"2\n{RUNNING_HEADER}\n서문\n왜 “사고 흐름”이 핵심인가\n이 플레이북은 특정 통계 기법을 가르치지 않는다."),
        _segment(2, f"3\n{RUNNING_HEADER}\nPART 1\n전체 사고 흐름 10단계\n열 개의 관문을 거친다."),
        _segment(3, f"4\n{RUNNING_HEADER}\n분석은 서랍 속 보고서로 남는다."),
        _segment(4, f"5\n{RUNNING_HEADER}\nPART 2\n공공데이터를 처음 받았을 때\n첫 10분 안에 확인할 것들."),
        _segment(5, "파일 형식·인코딩을 확인했다"),
        _segment(6, "전체 행/열 수를 파악했다"),
        _segment(7, f"6\n{RUNNING_HEADER}\nPART 3\n“한 행은 무엇인가?”\n그레인 판단법."),
    ]


def test_the_document_headings_are_recovered_in_source_order() -> None:
    outline = build_outline(_playbook())

    assert outline.ordered_headings == [
        "목차",
        "서문",
        "PART 1 전체 사고 흐름 10단계",
        "PART 2 공공데이터를 처음 받았을 때",
        "PART 3 “한 행은 무엇인가?”",
    ]


def test_a_segment_without_its_own_heading_inherits_the_one_above_it() -> None:
    outline = build_outline(_playbook())

    assert outline.heading_for("segment-5") == "PART 2 공공데이터를 처음 받았을 때"
    assert outline.heading_for("segment-6") == "PART 2 공공데이터를 처음 받았을 때"
    assert outline.heading_for("segment-3") == "PART 1 전체 사고 흐름 10단계"


def test_the_repeated_running_header_is_not_mistaken_for_a_heading() -> None:
    outline = build_outline(_playbook())

    assert RUNNING_HEADER not in outline.ordered_headings


def test_page_numbers_are_not_mistaken_for_headings() -> None:
    outline = build_outline(_playbook())

    assert all(not heading.strip().isdigit() for heading in outline.ordered_headings)


def test_markdown_headings_are_recovered() -> None:
    outline = build_outline([
        _segment(0, "# 배경\n프로젝트가 시작된 이유."),
        _segment(1, "본문이 이어진다."),
        _segment(2, "## 결론\n이렇게 하기로 한다."),
    ])

    assert outline.ordered_headings == ["배경", "결론"]
    assert outline.heading_for("segment-1") == "배경"


def test_numbered_sections_are_recovered() -> None:
    outline = build_outline([
        _segment(0, "1. 문제 정의\n무엇을 풀 것인가."),
        _segment(1, "2. 데이터 이해\n한 행은 무엇인가."),
    ])

    assert outline.ordered_headings == ["1. 문제 정의", "2. 데이터 이해"]


def test_a_document_with_no_headings_yields_an_empty_outline() -> None:
    outline = build_outline([_segment(0, "그냥 한 문단이다."), _segment(1, "또 한 문단이다.")])

    assert outline.ordered_headings == []
    assert outline.heading_for("segment-0") is None


def test_content_before_the_first_heading_keeps_its_position() -> None:
    """A cover page precedes the first heading and must not be pushed to the end."""
    outline = build_outline([
        _segment(0, "표지 문구입니다."),
        _segment(1, "# 배경\n프로젝트가 시작된 이유."),
    ])

    assert outline.heading_for("segment-0") is None
    assert outline.position_of("segment-0") < outline.position_of("segment-1")
