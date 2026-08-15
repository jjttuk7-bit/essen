from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import get_session
from app.main import create_app
from app.models.base import Base


def _client() -> TestClient:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def session_override() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = session_override
    return TestClient(app)


def test_diagnosis_returns_score_components_gaps_counts_and_explanations() -> None:
    client = _client()
    uploaded = client.post("/documents", files={"file": ("plan.txt", b"Action: deploy by Friday.", "text/plain")})
    document_id = uploaded.json()["document_id"]
    client.post(f"/documents/{document_id}/analyze")

    response = client.get(f"/documents/{document_id}/diagnosis")

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document_id
    assert body["analysis_run_id"]
    assert body["score_components"]["document_signal_score"] >= 0
    assert set(body["counts"]) >= {"segments", "semantic_slots", "gaps"}
    assert isinstance(body["gaps"], list)
    assert body["explanations"]
    assert body["labels"][0]["provenance"]["source_segment_id"]
    assert body["labels"][0]["reason"]


def test_diagnosis_returns_not_found_for_unknown_document() -> None:
    assert _client().get("/documents/missing/diagnosis").status_code == 404


def test_diagnosis_returns_conflict_until_document_is_analyzed() -> None:
    client = _client()
    uploaded = client.post("/documents", files={"file": ("draft.txt", b"Draft.", "text/plain")})

    assert client.get(f"/documents/{uploaded.json()['document_id']}/diagnosis").status_code == 409
