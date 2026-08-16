from fastapi.testclient import TestClient

from app.main import create_app


def test_cors_allows_configured_frontend_origin(monkeypatch):
    monkeypatch.setenv("CORS_ORIGIN", "https://app.example.com")

    response = TestClient(create_app()).options(
        "/documents",
        headers={"Origin": "https://app.example.com", "Access-Control-Request-Method": "POST"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://app.example.com"


def test_cors_rejects_unconfigured_origin(monkeypatch):
    monkeypatch.setenv("CORS_ORIGIN", "https://app.example.com")

    response = TestClient(create_app()).options(
        "/documents",
        headers={"Origin": "https://untrusted.example.com", "Access-Control-Request-Method": "POST"},
    )

    assert response.status_code == 400
