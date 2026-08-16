from dataclasses import dataclass

from app.services.diff.service import build_diff


@dataclass
class FakeSegment:
    id: str
    order_index: int
    text: str


@dataclass
class FakeLabel:
    segment_id: str
    label: str
    reason: str


def _provenance(*entries: tuple[int, str, str, str]) -> list[dict[str, object]]:
    return [
        {"section_index": index, "heading": heading, "text": "rendered", "source_slot_id": slot_id, "source_segment_id": segment_id}
        for index, heading, slot_id, segment_id in entries
    ]


def test_a_segment_rendered_alone_is_emphasized() -> None:
    segments = [FakeSegment("segment-1", 0, "Decision: launch pilot.")]
    provenance = _provenance((0, "Source-backed content", "slot-1", "segment-1"))

    entries = build_diff(segments, [], provenance)

    assert [entry.disposition for entry in entries] == ["EMPHASIZED"]
    assert entries[0].original_text == "Decision: launch pilot."
    assert entries[0].rendered_headings == ("Source-backed content",)
    assert "Source-backed content" in entries[0].reason


def test_segments_sharing_one_section_are_merged() -> None:
    segments = [FakeSegment("segment-1", 0, "First."), FakeSegment("segment-2", 1, "Second.")]
    provenance = _provenance(
        (0, "Executive summary", "slot-1", "segment-1"),
        (0, "Executive summary", "slot-2", "segment-2"),
    )

    entries = build_diff(segments, [], provenance)

    assert [entry.disposition for entry in entries] == ["MERGED", "MERGED"]
    assert "다른 1개 문단" in entries[0].reason


def test_a_segment_with_a_removable_label_is_removed_with_its_reason() -> None:
    segments = [FakeSegment("segment-1", 0, "As we all know, synergy matters.")]
    labels = [FakeLabel("segment-1", "GENERIC", "States a general truth without document-specific content.")]

    entries = build_diff(segments, labels, [])

    assert entries[0].disposition == "REMOVED"
    assert entries[0].reason == "States a general truth without document-specific content."
    assert entries[0].rendered_headings == ()


def test_an_unrendered_segment_without_a_removal_reason_is_held() -> None:
    segments = [FakeSegment("segment-1", 0, "Background note.")]

    entries = build_diff(segments, [], [])

    assert entries[0].disposition == "HELD"
    assert entries[0].reason == "지시·결론·주의·수치 근거가 없는 서술"


def test_a_rendered_segment_keeps_its_output_disposition_over_a_stale_label() -> None:
    segments = [FakeSegment("segment-1", 0, "Decision: launch pilot.")]
    labels = [FakeLabel("segment-1", "REDUNDANT", "Repeats an earlier point.")]
    provenance = _provenance((0, "Decisions", "slot-1", "segment-1"))

    entries = build_diff(segments, labels, provenance)

    assert entries[0].disposition == "EMPHASIZED"


def test_removed_candidate_sections_do_not_count_as_surviving_content() -> None:
    segments = [FakeSegment("segment-1", 0, "Filler sentence.")]
    labels = [FakeLabel("segment-1", "RHETORICAL", "Adds emphasis without new information.")]
    provenance = _provenance((0, "Removed candidates", "slot-1", "segment-1"))

    entries = build_diff(segments, labels, provenance)

    assert entries[0].disposition == "REMOVED"
    assert entries[0].reason == "Adds emphasis without new information."


def test_entries_follow_original_document_order() -> None:
    segments = [FakeSegment("segment-2", 1, "Second."), FakeSegment("segment-1", 0, "First.")]

    entries = build_diff(segments, [], [])

    assert [entry.segment_id for entry in entries] == ["segment-1", "segment-2"]


def test_a_dropped_segment_explains_itself_with_a_rule_reason() -> None:
    """"No semantic content" tells the reader nothing; the rule layer can name the ground."""
    segments = [FakeSegment("segment-1", 0, "일반적으로 데이터 품질은 매우 중요하다.")]

    entries = build_diff(segments, [], [], segment_texts={"segment-1": "일반적으로 데이터 품질은 매우 중요하다."})

    assert entries[0].disposition == "HELD"
    assert "일반론 표현" in entries[0].reason


def test_a_table_of_contents_segment_says_so() -> None:
    toc = "목차\nPART 1 개요\nPART 2 절차\nPART 3 검증"
    entries = build_diff([FakeSegment("segment-1", 0, toc)], [], [], segment_texts={"segment-1": toc})

    assert "목차" in entries[0].reason


def test_a_flattened_table_says_so() -> None:
    table = "축\n진단 질문\n흔한 문제\n일관성\n정확성"
    entries = build_diff([FakeSegment("segment-1", 0, table)], [], [], segment_texts={"segment-1": table})

    assert "표 조각" in entries[0].reason


def test_a_removal_label_still_wins_over_the_rule_reason() -> None:
    """A recorded removal decision is more specific than a generic shape reason."""
    segments = [FakeSegment("segment-1", 0, "일반적으로 중요하다.")]
    labels = [FakeLabel("segment-1", "REDUNDANT", "앞 문단과 같은 의미입니다.")]

    entries = build_diff(segments, labels, [], segment_texts={"segment-1": "일반적으로 중요하다."})

    assert entries[0].disposition == "REMOVED"
    assert entries[0].reason == "앞 문단과 같은 의미입니다."


def test_without_segment_texts_the_reason_still_exists() -> None:
    entries = build_diff([FakeSegment("segment-1", 0, "본문입니다.")], [], [])

    assert entries[0].reason


def test_plain_prose_says_which_signals_were_missing() -> None:
    """An absence the reader cannot check is not a reason; name what was looked for."""
    prose = "이 절에서는 배경을 설명하고 있다."
    entries = build_diff([FakeSegment("segment-1", 0, prose)], [], [], segment_texts={"segment-1": prose})

    assert entries[0].reason == "지시·결론·주의·수치 근거가 없는 서술"
