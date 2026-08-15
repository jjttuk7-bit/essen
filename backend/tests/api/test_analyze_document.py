from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import get_session
from app.main import create_app
from app.models.base import Base


def test_analyze_document_returns_source_linked_slots() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def session_override() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = session_override
    client = TestClient(app)
    uploaded = client.post("/documents", files={"file": ("plan.txt", b"Action: deploy by Friday.", "text/plain")})

    response = client.post(f"/documents/{uploaded.json()['document_id']}/analyze")

    assert response.status_code == 202
    body = response.json()
    assert body["purpose"] == "EXECUTE"
    assert body["semantic_slots"]
    assert all(slot["source_segment_id"] for slot in body["semantic_slots"])


def test_analyze_unknown_document_returns_not_found() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def session_override() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = session_override
    assert TestClient(app).post("/documents/missing/analyze").status_code == 404
