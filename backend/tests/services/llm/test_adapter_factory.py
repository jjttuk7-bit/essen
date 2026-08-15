from app.core.config import Settings
from app.schemas.llm import AnalysisRequest, SourceSegment
from app.services.llm.factory import create_llm_adapter
from app.services.llm.rule_based import RuleBasedLLMAdapter


def test_factory_uses_rule_based_provider_from_settings() -> None:
    settings = Settings(environment="test", host="127.0.0.1", port=8000, llm_provider="rule_based")

    assert isinstance(create_llm_adapter(settings), RuleBasedLLMAdapter)


def test_rule_based_adapter_returns_source_linked_multi_label_analysis() -> None:
    adapter = create_llm_adapter(
        Settings(environment="test", host="127.0.0.1", port=8000, llm_provider="rule_based")
    )

    analysis = adapter.analyze(
        AnalysisRequest(segments=[SourceSegment(id="segment-1", text="Action: deploy by Friday.")])
    )

    assert {slot.slot.value for slot in analysis.slots} >= {"FACT", "ACTION", "DEADLINE"}
    assert {slot.source_segment_id for slot in analysis.slots} == {"segment-1"}


def test_factory_rejects_unknown_provider() -> None:
    settings = Settings(environment="test", host="127.0.0.1", port=8000, llm_provider="unknown")

    try:
        create_llm_adapter(settings)
    except ValueError as error:
        assert "Unknown LLM provider" in str(error)
    else:
        raise AssertionError("Unknown provider must be rejected")


def test_openai_adapter_rejects_provider_slot_with_unknown_source_segment(monkeypatch) -> None:
    from app.services.llm.openai_compatible import OpenAICompatibleLLMAdapter

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self) -> bytes:
            return b'{"choices":[{"message":{"content":"{\\\"slots\\\":[{\\\"slot\\\":\\\"FACT\\\",\\\"text\\\":\\\"Unsupported source.\\\",\\\"source_segment_id\\\":\\\"invented-segment\\\",\\\"confidence\\\":0.8,\\\"importance\\\":0.8}]}"}}]}'

    monkeypatch.setattr("app.services.llm.openai_compatible.urlopen", lambda *args, **kwargs: FakeResponse())
    adapter = OpenAICompatibleLLMAdapter(base_url="https://llm.example", api_key="test-key", model="test-model")

    try:
        adapter.analyze(AnalysisRequest(segments=[SourceSegment(id="segment-1", text="Known source.")]))
    except ValueError as error:
        assert "source_segment_id" in str(error)
    else:
        raise AssertionError("Provider slots with unknown sources must be rejected")
