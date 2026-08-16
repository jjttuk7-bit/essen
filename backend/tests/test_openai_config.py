from app.core.config import get_settings


def test_openai_api_key_is_read_from_the_environment(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    assert get_settings().openai_api_key == "sk-test-key"


def test_missing_openai_api_key_leaves_the_key_empty(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert get_settings().openai_api_key == ""


def test_openai_model_defaults_to_gpt_5_mini(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    assert get_settings().openai_model == "gpt-5-mini"


def test_openai_model_is_overridden_by_the_environment(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5")

    assert get_settings().openai_model == "gpt-5"


def test_cors_origin_is_read_as_one_exact_origin(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGIN", "https://app.example.com")

    assert get_settings().cors_origin == "https://app.example.com"


def test_missing_cors_origin_allows_no_browser_origin(monkeypatch) -> None:
    monkeypatch.delenv("CORS_ORIGIN", raising=False)

    assert get_settings().cors_origin == ""
