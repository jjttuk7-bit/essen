from app.services.parser.service import DocumentParserService


def test_text_parser_creates_ordered_paragraph_segments() -> None:
    parsed = DocumentParserService().parse(
        filename="brief.txt",
        content=b"First paragraph.\n\nSecond paragraph.",
    )

    assert parsed.source_type.value == "text"
    assert [(segment.order_index, segment.paragraph) for segment in parsed.segments] == [(0, 1), (1, 2)]
    assert [segment.text for segment in parsed.segments] == ["First paragraph.", "Second paragraph."]


def test_markdown_parser_normalizes_line_endings_without_changing_paragraph_text() -> None:
    parsed = DocumentParserService().parse(
        filename="brief.md",
        content=b"# Brief\r\n\r\nFirst paragraph.\r\n\r\nSecond paragraph.",
    )

    assert parsed.raw_text == "# Brief\n\nFirst paragraph.\n\nSecond paragraph."
    assert [segment.paragraph for segment in parsed.segments] == [1, 2, 3]
