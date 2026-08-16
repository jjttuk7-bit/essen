import pytest
from pydantic import ValidationError

from app.schemas.semantic import SemanticSlotPayload, ValidatedAnalysis


def test_schema_rejects_an_unknown_semantic_slot() -> None:
    with pytest.raises(ValidationError):
        SemanticSlotPayload.model_validate(
            {
                "slot": "INVENTED_SLOT",
                "text": "A source-backed statement.",
                "source_segment_id": "segment-1",
                "confidence": 0.8,
                "importance": 0.7,
            }
        )


def test_schema_rejects_a_blank_source_segment_id() -> None:
    with pytest.raises(ValidationError):
        SemanticSlotPayload.model_validate(
            {
                "slot": "FACT",
                "text": "A source-backed statement.",
                "source_segment_id": "  ",
                "confidence": 0.8,
                "importance": 0.7,
            }
        )


def test_validated_analysis_accepts_multiple_labels_for_one_segment() -> None:
    analysis = ValidatedAnalysis.model_validate(
        {
            "slots": [
                {"slot": "FACT", "text": "Deploy Friday.", "source_segment_id": "segment-1", "confidence": 0.8, "importance": 0.8},
                {"slot": "DEADLINE", "text": "Friday", "source_segment_id": "segment-1", "confidence": 0.9, "importance": 0.8},
            ]
        }
    )

    assert [slot.slot.value for slot in analysis.slots] == ["FACT", "DEADLINE"]


def test_a_provider_http_error_carries_the_provider_explanation(monkeypatch) -> None:
    """A bare "HTTP Error 400" hides why the provider refused; keep its message."""
    import io
    from urllib.error import HTTPError

    from app.schemas.llm import AnalysisRequest, SourceSegment
    from app.services.llm.openai_compatible import OpenAICompatibleLLMAdapter

    def raise_http_error(*_args, **_kwargs):
        body = io.BytesIO(b'{"error":{"message":"Invalid schema: required is required to be supplied and to be an array including every key in properties."}}')
        raise HTTPError("https://api.openai.com/v1/chat/completions", 400, "Bad Request", {}, body)

    monkeypatch.setattr("app.services.llm.openai_compatible.urlopen", raise_http_error)
    adapter = OpenAICompatibleLLMAdapter(base_url="https://api.openai.com/v1", api_key="k", model="gpt-5-mini")

    try:
        adapter.analyze(AnalysisRequest(segments=[SourceSegment(id="segment-1", text="Known source.")]))
    except RuntimeError as error:
        assert "400" in str(error)
        assert "required is required to be supplied" in str(error)
    else:
        raise AssertionError("Provider HTTP errors must surface the provider message")


def test_the_request_sends_the_strict_wire_schema(monkeypatch) -> None:
    import json as json_module

    from app.schemas.llm import AnalysisRequest, SourceSegment
    from app.services.llm.openai_compatible import OpenAICompatibleLLMAdapter
    from app.services.llm.strict_schema import ANALYSIS_JSON_SCHEMA

    captured: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self) -> bytes: return b'{"choices":[{"message":{"content":"{\\"slots\\":[]}"}}]}'

    def capture(request, *_args, **_kwargs):
        captured.update(json_module.loads(request.data.decode("utf-8")))
        return FakeResponse()

    monkeypatch.setattr("app.services.llm.openai_compatible.urlopen", capture)
    OpenAICompatibleLLMAdapter(base_url="https://api.openai.com/v1", api_key="k", model="gpt-5-mini").analyze(
        AnalysisRequest(segments=[SourceSegment(id="segment-1", text="Known source.")])
    )

    assert captured["response_format"]["json_schema"]["schema"] == ANALYSIS_JSON_SCHEMA
    assert captured["response_format"]["json_schema"]["strict"] is True
