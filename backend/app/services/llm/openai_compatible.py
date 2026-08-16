import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.schemas.llm import AnalysisRequest
from app.schemas.semantic import ValidatedAnalysis, validate_analysis_source_context
from app.services.llm.base import LLMAdapter
from app.services.llm.strict_schema import ANALYSIS_JSON_SCHEMA


class OpenAICompatibleLLMAdapter(LLMAdapter):
    """OpenAI chat-completions adapter that requires schema-conforming JSON."""

    def __init__(self, *, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def analyze(self, request: AnalysisRequest) -> ValidatedAnalysis:
        if not self.base_url or not self.api_key or not self.model:
            raise ValueError("OpenAI-compatible provider requires base URL, API key, and model")
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": self._prompt()}, {"role": "user", "content": request.model_dump_json()}],
            "response_format": {"type": "json_schema", "json_schema": {"name": "semantic_analysis", "strict": True, "schema": ANALYSIS_JSON_SCHEMA}},
        }
        http_request = Request(f"{self.base_url}/chat/completions", data=json.dumps(payload).encode("utf-8"), headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(http_request, timeout=30) as response:  # noqa: S310 - configured provider endpoint
                envelope = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            # urllib's HTTPError renders as a bare status line; the provider explains the
            # rejection in the response body, so carry that into the message.
            raise RuntimeError(f"OpenAI request failed with HTTP {error.code}: {self._error_detail(error)}") from error
        content = envelope["choices"][0]["message"]["content"]
        provider_json = json.loads(content) if isinstance(content, str) else content
        analysis = ValidatedAnalysis.model_validate(provider_json)
        return validate_analysis_source_context(analysis, {segment.id for segment in request.segments})

    @staticmethod
    def _error_detail(error: HTTPError) -> str:
        try:
            body = error.read().decode("utf-8", errors="replace")
        except Exception:
            return error.reason or "no response body"
        try:
            return json.loads(body).get("error", {}).get("message") or body[:500]
        except ValueError:
            return body[:500]

    @staticmethod
    def _prompt() -> str:
        return Path(__file__).resolve().parents[2].joinpath("prompts", "semantic_extraction_v1.md").read_text(encoding="utf-8")


