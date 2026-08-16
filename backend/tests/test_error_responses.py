from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import get_session
from app.main import create_app
from app.models.base import Base

ORIGIN = "https://app.example.com"


@pytest.fixture(autouse=True)
def configured_origin(monkeypatch):
    monkeypatch.setenv("CORS_ORIGIN", ORIGIN)


def _failing_client(monkeypatch) -> TestClient:
    from app.services.semantic.service import SemanticExtractionService

    def explode(*_args, **_kwargs):
        raise RuntimeError("provider rejected the request")

    monkeypatch.setattr(SemanticExtractionService, "analyze_document", explode)
    return TestClient(create_app(), raise_server_exceptions=False)


def test_an_unhandled_error_still_carries_cors_headers(monkeypatch) -> None:
    """Without CORS headers a browser reports "Failed to fetch" and hides the real error."""
    response = _failing_client(monkeypatch).post(
        "/documents/any-id/analyze", headers={"Origin": ORIGIN}
    )

    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == ORIGIN


def test_an_unhandled_error_returns_a_readable_json_detail(monkeypatch) -> None:
    response = _failing_client(monkeypatch).post(
        "/documents/any-id/analyze", headers={"Origin": ORIGIN}
    )

    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"]


def test_the_error_body_does_not_leak_internals(monkeypatch) -> None:
    response = _failing_client(monkeypatch).post(
        "/documents/any-id/analyze", headers={"Origin": ORIGIN}
    )

    assert "provider rejected the request" not in response.text
    assert "Traceback" not in response.text


def test_handled_http_errors_keep_their_status_and_detail() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def session_override() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = session_override

    response = TestClient(app).get("/documents/missing/diagnosis", headers={"Origin": ORIGIN})

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"
    assert response.headers["access-control-allow-origin"] == ORIGIN
