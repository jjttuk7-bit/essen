from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import get_session
from app.main import create_app
from app.models.base import Base
from app.models.document import Document


def test_uploading_text_persists_document_and_ordered_segments() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def session_override() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = session_override
    response = TestClient(app).post(
        "/documents",
        files={"file": ("brief.txt", b"First paragraph.\n\nSecond paragraph.", "text/plain")},
    )

    assert response.status_code == 201
    assert response.json()["source_type"] == "text"
    assert response.json()["segment_count"] == 2
    with Session(engine) as session:
        document = session.scalar(select(Document))
        assert document is not None
        assert [(segment.order_index, segment.paragraph) for segment in document.segments] == [(0, 1), (1, 2)]


def test_uploading_empty_text_layer_pdf_returns_unprocessable_entity() -> None:
    response = TestClient(create_app()).post(
        "/documents",
        files={"file": ("scan.pdf", b"%PDF-1.4\n% empty scan", "application/pdf")},
    )

    assert response.status_code == 422
    assert "text" in response.json()["detail"].lower()

def test_upload_over_size_limit_returns_413_without_reading_all_content_or_parsing(monkeypatch) -> None:
    from app.api import documents
    from starlette.datastructures import UploadFile as StarletteUploadFile

    def parsing_must_not_run(*args, **kwargs):
        raise AssertionError("the parser must not receive oversized content")

    read_sizes: list[int] = []
    original_read = StarletteUploadFile.read

    async def recording_read(upload, size: int = -1):
        read_sizes.append(size)
        return await original_read(upload, size)

    monkeypatch.setattr(documents.DocumentParserService, "parse", parsing_must_not_run)
    monkeypatch.setattr(StarletteUploadFile, "read", recording_read)
    response = TestClient(create_app()).post(
        "/documents",
        files={"file": ("large.txt", b"x" * (documents.MAX_UPLOAD_BYTES + 1), "text/plain")},
    )

    assert response.status_code == 413
    assert -1 not in read_sizes


def _upload_client() -> TestClient:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def session_override() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = session_override
    return TestClient(app)


def test_uploading_a_valid_two_megabyte_file_reaches_the_endpoint(monkeypatch) -> None:
    from app.api.documents import DocumentParserService
    from app.models.document import SourceType
    from app.services.parser.base import ParsedDocument, ParsedSegment

    monkeypatch.setattr(DocumentParserService, "parse", lambda *_args, **_kwargs: ParsedDocument(SourceType.TEXT, "accepted", [ParsedSegment(0, "accepted", None, 1)]))
    response = _upload_client().post(
        "/documents",
        files={"file": ("two-megabytes.txt", b"x" * (2 * 1024 * 1024), "text/plain")},
    )
    assert response.status_code == 201


def test_uploading_an_exactly_ten_megabyte_file_is_accepted(monkeypatch) -> None:
    from app.api.documents import DocumentParserService
    from app.models.document import SourceType
    from app.services.parser.base import ParsedDocument, ParsedSegment

    monkeypatch.setattr(DocumentParserService, "parse", lambda *_args, **_kwargs: ParsedDocument(SourceType.TEXT, "accepted", [ParsedSegment(0, "accepted", None, 1)]))
    response = _upload_client().post(
        "/documents",
        files={"file": ("ten-megabytes.txt", b"x" * (10 * 1024 * 1024), "text/plain")},
    )
    assert response.status_code == 201

def test_malformed_multipart_body_remains_a_400_error() -> None:
    response = TestClient(create_app()).post(
        "/documents",
        content=b"not-a-valid-multipart-body",
        headers={"content-type": "multipart/form-data; boundary=boundary"},
    )
    assert response.status_code == 400

CONTRACT = """소프트웨어 개발 용역 계약서

주식회사 가나(이하 "갑"이라 한다)와 주식회사 다라(이하 "을"이라 한다)는 다음과 같이 계약을 체결한다.

제1조 (목적) 본 계약은 갑이 을에게 위탁하는 용역의 조건을 정함을 목적으로 한다.

제2조 (계약금액) 계약금액은 금 오천만원으로 한다.

제3조 (손해배상) 을이 납기를 지연한 경우 계약금액의 1000분의 3을 배상한다.

제4조 (해지) 갑은 을이 본 계약을 위반한 경우 계약을 해지할 수 있다.

본 계약을 증명하기 위하여 계약서 2부를 작성하여 각각 서명 날인 후 보관한다."""


def test_a_contract_is_declined_with_a_reason() -> None:
    response = _upload_client().post("/documents", files={"file": ("contract.txt", CONTRACT.encode(), "text/plain")})

    assert response.status_code == 422
    assert "계약서" in response.json()["detail"]


def test_a_declined_document_is_never_stored() -> None:
    """Refusing after storing would keep a contract we told the user we would not handle."""
    client = _upload_client()

    client.post("/documents", files={"file": ("contract.txt", CONTRACT.encode(), "text/plain")})

    assert client.get("/documents/any/diff").status_code == 404


def test_an_ordinary_document_is_still_accepted() -> None:
    minutes = "2026년 3월 12일\n참석: 김민수, 이서연\n\n안건 1. 일정\n연기하기로 결정했다. 담당: 김민수."
    response = _upload_client().post("/documents", files={"file": ("minutes.txt", minutes.encode(), "text/plain")})

    assert response.status_code == 201
