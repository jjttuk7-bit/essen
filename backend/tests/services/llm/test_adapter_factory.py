from app.core.config import Settings
from app.schemas.llm import AnalysisRequest, SourceSegment
from app.services.llm.factory import create_llm_adapter
from app.services.llm.openai_compatible import OpenAICompatibleLLMAdapter
from app.services.llm.rule_based import RuleBasedLLMAdapter


def _settings(**overrides) -> Settings:
    return Settings(environment="test", host="127.0.0.1", port=8000, **overrides)


def test_factory_uses_the_rule_based_adapter_without_an_api_key() -> None:
    assert isinstance(create_llm_adapter(_settings()), RuleBasedLLMAdapter)


def test_factory_uses_openai_with_the_fixed_base_url_and_default_model() -> None:
    adapter = create_llm_adapter(_settings(openai_api_key="sk-test-key"))

    assert isinstance(adapter, OpenAICompatibleLLMAdapter)
    assert adapter.base_url == "https://api.openai.com/v1"
    assert adapter.model == "gpt-5-mini"
    assert adapter.api_key == "sk-test-key"


def test_factory_honors_an_overridden_model() -> None:
    adapter = create_llm_adapter(_settings(openai_api_key="sk-test-key", openai_model="gpt-5"))

    assert adapter.model == "gpt-5"


def test_rule_based_adapter_returns_source_linked_multi_label_analysis() -> None:
    adapter = create_llm_adapter(_settings())

    analysis = adapter.analyze(
        AnalysisRequest(segments=[SourceSegment(id="segment-1", text="Action: deploy by Friday.")])
    )

    assert {slot.slot.value for slot in analysis.slots} >= {"FACT", "ACTION", "DEADLINE"}
    assert {slot.source_segment_id for slot in analysis.slots} == {"segment-1"}


def test_openai_adapter_rejects_provider_slot_with_unknown_source_segment(monkeypatch) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self) -> bytes:
            return b'{"choices":[{"message":{"content":"{\\\"slots\\\":[{\\\"slot\\\":\\\"FACT\\\",\\\"text\\\":\\\"Unsupported source.\\\",\\\"source_segment_id\\\":\\\"invented-segment\\\",\\\"confidence\\\":0.8,\\\"importance\\\":0.8}]}"}}]}'

    monkeypatch.setattr("app.services.llm.openai_compatible.urlopen", lambda *args, **kwargs: FakeResponse())
    adapter = create_llm_adapter(_settings(openai_api_key="sk-test-key"))

    try:
        adapter.analyze(AnalysisRequest(segments=[SourceSegment(id="segment-1", text="Known source.")]))
    except ValueError as error:
        assert "source_segment_id" in str(error)
    else:
        raise AssertionError("Provider slots with unknown sources must be rejected")
