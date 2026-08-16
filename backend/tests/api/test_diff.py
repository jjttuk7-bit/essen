from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import get_session
from app.main import create_app
from app.models.base import Base

DOCUMENT = b"Decision: launch pilot.\n\nAction: Kim deploy by Friday.\n\nAs we all know, quality matters a great deal."


def _client() -> TestClient:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def session_override() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = session_override
    return TestClient(app)


def _analyzed_and_rendered(client: TestClient) -> str:
    document_id = client.post("/documents", files={"file": ("plan.txt", DOCUMENT, "text/plain")}).json()["document_id"]
    client.post(f"/documents/{document_id}/analyze")
    client.post(f"/documents/{document_id}/render")
    return document_id


def test_diff_covers_every_source_segment_exactly_once_with_a_reason() -> None:
    client = _client()
    document_id = _analyzed_and_rendered(client)

    response = client.get(f"/documents/{document_id}/diff")

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document_id
    assert body["output_type"] == "clean_version"
    segment_ids = [entry["segment_id"] for entry in body["entries"]]
    assert len(segment_ids) == len(set(segment_ids)) == 3
    assert all(entry["reason"] for entry in body["entries"])
    assert all(entry["original_text"] for entry in body["entries"])
    assert all(entry["disposition"] in {"REMOVED", "MERGED", "EMPHASIZED", "HELD"} for entry in body["entries"])


def test_diff_entries_are_ordered_and_counted_by_disposition() -> None:
    client = _client()
    document_id = _analyzed_and_rendered(client)

    body = client.get(f"/documents/{document_id}/diff").json()

    assert [entry["order_index"] for entry in body["entries"]] == [0, 1, 2]
    assert sum(body["counts"].values()) == len(body["entries"])
    assert set(body["counts"]) == {"REMOVED", "MERGED", "EMPHASIZED", "HELD"}


def test_diff_reports_the_bottlenecks_the_document_carries() -> None:
    client = _client()
    document_id = _analyzed_and_rendered(client)

    body = client.get(f"/documents/{document_id}/diff").json()

    assert isinstance(body["bottlenecks"], list)
    assert all(finding["label"] and finding["detail"] for finding in body["bottlenecks"])


def test_diff_rejects_an_unknown_output_type() -> None:
    client = _client()
    document_id = _analyzed_and_rendered(client)

    assert client.get(f"/documents/{document_id}/diff", params={"output_type": "nope"}).status_code == 422


def test_diff_requires_a_rendered_output() -> None:
    client = _client()
    document_id = client.post("/documents", files={"file": ("plan.txt", DOCUMENT, "text/plain")}).json()["document_id"]
    client.post(f"/documents/{document_id}/analyze")

    response = client.get(f"/documents/{document_id}/diff")

    assert response.status_code == 409
    assert "render" in response.json()["detail"].lower()


def test_diff_returns_not_found_for_an_unknown_document() -> None:
    assert _client().get("/documents/missing/diff").status_code == 404


REPEATED = (
    b"Decision: we will launch the pilot in Q3.\n\n"
    b"Revenue grew 20% year over year according to the finance report.\n\n"
    b"Revenue grew 20% year over year according to the finance report."
)


def test_rendering_removes_labeled_content_without_a_prior_diagnosis_call() -> None:
    """Quality labels must exist by render time, not only after /diagnosis is requested."""
    client = _client()
    document_id = client.post("/documents", files={"file": ("plan.txt", REPEATED, "text/plain")}).json()["document_id"]
    client.post(f"/documents/{document_id}/analyze")

    rendered = client.post(f"/documents/{document_id}/render")
    body = client.get(f"/documents/{document_id}/diff").json()

    assert rendered.status_code == 201
    assert body["counts"]["REMOVED"] == 1
    removed = [entry for entry in body["entries"] if entry["disposition"] == "REMOVED"]
    assert removed[0]["reason"]
    assert removed[0]["rendered_headings"] == []


def test_render_reaches_the_same_result_whether_or_not_diagnosis_ran_first() -> None:
    def counts(diagnose_first: bool) -> dict[str, int]:
        client = _client()
        document_id = client.post("/documents", files={"file": ("plan.txt", REPEATED, "text/plain")}).json()["document_id"]
        client.post(f"/documents/{document_id}/analyze")
        if diagnose_first:
            client.get(f"/documents/{document_id}/diagnosis")
        client.post(f"/documents/{document_id}/render")
        return client.get(f"/documents/{document_id}/diff").json()["counts"]

    assert counts(diagnose_first=True) == counts(diagnose_first=False)
