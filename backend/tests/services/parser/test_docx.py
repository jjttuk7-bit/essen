"""Word documents, which is what most of these documents actually arrive as.

A .docx is a zip holding one XML part, so extraction needs no third-party reader. What
matters is that it comes out shaped the way the rest of the pipeline expects: paragraphs
separated, and table rows kept on their own lines so the shape rules can still see a table.
"""

import io
import zipfile

import pytest

from app.services.parser.base import ParseError
from app.services.parser.docx import DocxParser

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _paragraph(text: str) -> str:
    runs = "".join(f"<w:r><w:t>{part}</w:t></w:r>" for part in text.split("|"))
    return f"<w:p>{runs}</w:p>"


def _table(rows: list[list[str]]) -> str:
    cells = "".join(
        "<w:tr>" + "".join(f"<w:tc>{_paragraph(cell)}</w:tc>" for cell in row) + "</w:tr>"
        for row in rows
    )
    return f"<w:tbl>{cells}</w:tbl>"


def _docx(*body: str) -> bytes:
    document = f'<?xml version="1.0"?><w:document xmlns:w="{W}"><w:body>{"".join(body)}</w:body></w:document>'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


class TestReadingText:
    def test_paragraphs_become_separate_segments(self) -> None:
        parsed = DocxParser().parse(_docx(_paragraph("첫 문단입니다."), _paragraph("둘째 문단입니다.")))

        assert [segment.text for segment in parsed.segments] == ["첫 문단입니다.", "둘째 문단입니다."]

    def test_runs_inside_a_paragraph_are_joined(self) -> None:
        """Word splits a sentence across runs wherever formatting changes."""
        parsed = DocxParser().parse(_docx(_paragraph("결정: |오픈일을 |2주 연기한다.")))

        assert parsed.segments[0].text == "결정: 오픈일을 2주 연기한다."

    def test_empty_paragraphs_are_skipped(self) -> None:
        parsed = DocxParser().parse(_docx(_paragraph("본문."), "<w:p/>", _paragraph("다음 문단.")))

        assert len(parsed.segments) == 2

    def test_segments_are_numbered_in_document_order(self) -> None:
        parsed = DocxParser().parse(_docx(_paragraph("하나."), _paragraph("둘."), _paragraph("셋.")))

        assert [segment.order_index for segment in parsed.segments] == [0, 1, 2]


class TestTables:
    def test_a_table_becomes_one_segment_with_a_row_per_line(self) -> None:
        """Row-per-line is what lets the shape rules recognise it as a table later."""
        parsed = DocxParser().parse(_docx(_table([["단계", "산출물"], ["문제정의", "문제정의서"], ["품질진단", "리포트"]])))

        assert parsed.segments[0].text.split("\n") == ["단계\t산출물", "문제정의\t문제정의서", "품질진단\t리포트"]

    def test_a_table_is_recognized_by_the_shape_rules(self) -> None:
        from app.services.selection.rules import Shape, classify_shape

        parsed = DocxParser().parse(_docx(_table([["축", "질문"], ["완전성", "빠짐없나"], ["일관성", "같은가"], ["정확성", "맞는가"]])))

        assert classify_shape(parsed.segments[0].text) is Shape.TABLE

    def test_prose_around_a_table_stays_separate(self) -> None:
        parsed = DocxParser().parse(_docx(_paragraph("아래 표를 확인한다."), _table([["가", "나"]]), _paragraph("이상이다.")))

        assert len(parsed.segments) == 3
        assert parsed.segments[0].text == "아래 표를 확인한다."


class TestRefusingWhatItCannotRead:
    def test_a_file_that_is_not_a_zip_is_rejected(self) -> None:
        with pytest.raises(ParseError, match="Word"):
            DocxParser().parse(b"this is not a docx")

    def test_a_zip_without_a_document_part_is_rejected(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("hello.txt", "not a word file")

        with pytest.raises(ParseError, match="Word"):
            DocxParser().parse(buffer.getvalue())

    def test_a_document_with_no_text_is_rejected(self) -> None:
        with pytest.raises(ParseError, match="no text"):
            DocxParser().parse(_docx("<w:p/>", "<w:p/>"))
