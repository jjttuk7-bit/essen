import pytest


@pytest.fixture(autouse=True)
def isolate_openai_environment(monkeypatch):
    """Keep the suite offline and deterministic regardless of ambient credentials.

    ``create_llm_adapter`` selects OpenAI whenever ``OPENAI_API_KEY`` is present, so a
    developer key in the shell would otherwise send test runs to the real API. Tests that
    exercise OpenAI selection build ``Settings`` explicitly instead of reading the env.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
