"""Korean word-processor formats, which is what the target users actually send.

HWPX is a zip of XML and yields to the same treatment as .docx. Legacy .hwp is an OLE
container of zlib-compressed tagged records, and its paragraph text carries inline
control codes: most occupy eight UTF-16 code units rather than one, so stepping over them
by the wrong width turns the remainder of the paragraph into noise. The record walk and
the control decoding are therefore tested directly, without building an OLE container.
"""

import io
import zipfile

import pytest

from app.services.parser.base import ParseError
from app.services.parser.hwp import HWPTAG_PARA_TEXT, decode_paragraph, paragraphs_in_section
from app.services.parser.hwpx import HwpxParser

HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"


def _units(*values: int) -> bytes:
    return b"".join(value.to_bytes(2, "little") for value in values)


def _text(value: str) -> bytes:
    return value.encode("utf-16-le")


def _record(tag: int, payload: bytes) -> bytes:
    header = (tag & 0x3FF) | (len(payload) << 20)
    return header.to_bytes(4, "little") + payload


class TestDecodingParagraphText:
    def test_plain_text_survives(self) -> None:
        assert decode_paragraph(_text("결정 사항입니다.")) == "결정 사항입니다."

    def test_a_tab_control_becomes_a_tab(self) -> None:
        """Code 9 is a tab, and like most controls it occupies eight code units."""
        payload = _text("담당") + _units(9, 0, 0, 0, 0, 0, 0, 9) + _text("김민수")

        assert decode_paragraph(payload) == "담당\t김민수"

    def test_a_line_break_becomes_a_newline(self) -> None:
        assert decode_paragraph(_text("첫 줄") + _units(10) + _text("둘째 줄")) == "첫 줄\n둘째 줄"

    def test_an_anchored_object_is_stepped_over_without_eating_the_text(self) -> None:
        """The twelve payload bytes are not text; misreading the width corrupts the rest."""
        payload = _text("표") + _units(11, 0, 0, 0, 0, 0, 0, 11) + _text("아래 참조")

        assert decode_paragraph(payload) == "표아래 참조"

    def test_a_narrow_control_advances_by_one(self) -> None:
        assert decode_paragraph(_text("가") + _units(24) + _text("나")) == "가나"

    def test_an_odd_trailing_byte_does_not_crash(self) -> None:
        assert decode_paragraph(_text("가나") + b"\x41") == "가나"

    def test_an_empty_payload_is_empty(self) -> None:
        assert decode_paragraph(b"") == ""


class TestWalkingTheRecordStream:
    def test_paragraph_records_are_collected_in_order(self) -> None:
        section = _record(HWPTAG_PARA_TEXT, _text("첫째")) + _record(HWPTAG_PARA_TEXT, _text("둘째"))

        assert paragraphs_in_section(section) == ["첫째", "둘째"]

    def test_other_records_are_skipped_without_losing_alignment(self) -> None:
        # Neither neighbour may collide with HWPTAG_PARA_TEXT, which is 0x43.
        section = _record(0x50, b"\x00" * 6) + _record(HWPTAG_PARA_TEXT, _text("본문")) + _record(0x51, b"\x01\x02")

        assert paragraphs_in_section(section) == ["본문"]

    def test_an_extended_size_record_is_read_from_its_second_word(self) -> None:
        payload = _text("긴 문단")
        header = (HWPTAG_PARA_TEXT & 0x3FF) | (0xFFF << 20)
        section = header.to_bytes(4, "little") + len(payload).to_bytes(4, "little") + payload

        assert paragraphs_in_section(section) == ["긴 문단"]

    def test_a_truncated_stream_stops_rather_than_crashing(self) -> None:
        assert paragraphs_in_section(_record(HWPTAG_PARA_TEXT, _text("본문"))[:-3]) == [""]

    def test_an_empty_stream_yields_nothing(self) -> None:
        assert paragraphs_in_section(b"") == []


def _hwpx(*body: str) -> bytes:
    document = f'<?xml version="1.0"?><hp:sec xmlns:hp="{HP}">{"".join(body)}</hp:sec>'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", "application/hwp+zip")
        archive.writestr("Contents/section0.xml", document)
    return buffer.getvalue()


def _para(text: str) -> str:
    return f"<hp:p><hp:run><hp:t>{text}</hp:t></hp:run></hp:p>"


class TestHwpx:
    def test_paragraphs_become_segments(self) -> None:
        parsed = HwpxParser().parse(_hwpx(_para("첫 문단."), _para("둘째 문단.")))

        assert [segment.text for segment in parsed.segments] == ["첫 문단.", "둘째 문단."]

    def test_a_table_inside_a_paragraph_becomes_its_own_block(self) -> None:
        """HWPX nests the table in the paragraph, so prose and table must be separated."""
        rows = "".join(
            "<hp:tr>" + "".join(f"<hp:tc>{_para(cell)}</hp:tc>" for cell in row) + "</hp:tr>"
            for row in (["단계", "산출물"], ["문제정의", "문제정의서"])
        )
        parsed = HwpxParser().parse(_hwpx(f"<hp:p><hp:run><hp:t>아래 표.</hp:t><hp:tbl>{rows}</hp:tbl></hp:run></hp:p>"))

        assert [segment.text for segment in parsed.segments] == ["아래 표.", "단계\t산출물\n문제정의\t문제정의서"]

    def test_sections_are_read_in_numeric_order(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for index, text in ((10, "열번째"), (2, "두번째"), (0, "처음")):
                archive.writestr(f"Contents/section{index}.xml", f'<?xml version="1.0"?><hp:sec xmlns:hp="{HP}">{_para(text)}</hp:sec>')

        assert [segment.text for segment in HwpxParser().parse(buffer.getvalue()).segments] == ["처음", "두번째", "열번째"]

    @pytest.mark.parametrize("content", [b"not a zip", b"PK\x03\x04broken"])
    def test_unreadable_input_is_rejected(self, content: bytes) -> None:
        with pytest.raises(ParseError, match="HWPX"):
            HwpxParser().parse(content)

    def test_a_zip_without_sections_is_rejected(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("mimetype", "application/hwp+zip")

        with pytest.raises(ParseError, match="HWPX"):
            HwpxParser().parse(buffer.getvalue())
