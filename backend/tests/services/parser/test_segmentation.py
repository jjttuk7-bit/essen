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


def test_normalize_text_strips_nul_characters() -> None:
    """Postgres rejects NUL in text literals; PDF extraction can emit them."""
    from app.services.parser.base import normalize_text

    assert normalize_text("Revenue\x00 grew\x00 20%.") == "Revenue grew 20%."


def test_parsed_text_uploads_carry_no_nul_characters() -> None:
    parsed = DocumentParserService().parse(
        filename="brief.txt",
        content="First\x00 paragraph.\n\nSecond paragraph.".encode(),
    )

    assert "\x00" not in parsed.raw_text
    assert all("\x00" not in segment.text for segment in parsed.segments)
    assert parsed.segments[0].text == "First paragraph."
