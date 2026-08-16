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


def test_render_persists_all_requested_provenance_safe_outputs() -> None:
    client = _client()
    uploaded = client.post(
        "/documents",
        files={"file": ("plan.txt", b"Decision: launch pilot.\\n\\nAction: Kim deploy by Friday.", "text/plain")},
    )
    document_id = uploaded.json()["document_id"]
    client.post(f"/documents/{document_id}/analyze")

    response = client.post(f"/documents/{document_id}/render")

    assert response.status_code == 201
    outputs = response.json()["outputs"]
    assert {output["output_type"] for output in outputs} == {
        "clean_version", "executive_summary", "action_decision_sheet"
    }
    assert all(section["source_slot_ids"] for output in outputs for section in output["sections"])


def test_outputs_returns_not_found_and_requires_completed_analysis() -> None:
    client = _client()
    assert client.get("/documents/missing/outputs").status_code == 404
    uploaded = client.post("/documents", files={"file": ("draft.txt", b"Draft.", "text/plain")})
    assert client.post(f"/documents/{uploaded.json()['document_id']}/render").status_code == 409


def test_render_accepts_a_targeted_output_request_and_is_idempotent() -> None:
    client = _client()
    uploaded = client.post("/documents", files={"file": ("plan.txt", b"Decision: launch pilot.", "text/plain")})
    document_id = uploaded.json()["document_id"]
    client.post(f"/documents/{document_id}/analyze")

    first = client.post(f"/documents/{document_id}/render", json={"output_type": "executive_summary", "audience": "CEO", "max_words": 50})
    second = client.post(f"/documents/{document_id}/render", json={"output_type": "executive_summary", "audience": "CEO", "max_words": 50})
    outputs = client.get(f"/documents/{document_id}/outputs")

    assert first.status_code == second.status_code == 201
    assert [output["output_type"] for output in first.json()["outputs"]] == ["executive_summary"]
    section = first.json()["outputs"][0]["sections"][0]
    assert section["source_segment_ids"]
    assert len(section["source_segment_ids"]) == len(section["source_slot_ids"])
    assert len(outputs.json()["outputs"]) == 1


def test_rendering_different_configs_preserves_versioned_output_history() -> None:
    client = _client()
    uploaded = client.post("/documents", files={"file": ("plan.txt", b"Decision: launch pilot.", "text/plain")})
    document_id = uploaded.json()["document_id"]
    client.post(f"/documents/{document_id}/analyze")

    ceo = client.post(f"/documents/{document_id}/render", json={"output_type": "executive_summary", "audience": "CEO", "max_words": 50})
    operator = client.post(f"/documents/{document_id}/render", json={"output_type": "executive_summary", "audience": "Operator", "max_words": 25})
    outputs = client.get(f"/documents/{document_id}/outputs").json()["outputs"]

    assert ceo.status_code == operator.status_code == 201
    assert len(outputs) == 2
    assert sorted(output["version"] for output in outputs) == [1, 2]
    assert {output["audience"] for output in outputs} == {"CEO", "Operator"}
    assert len({output["render_config_hash"] for output in outputs}) == 2
