from app.core.config import Settings
from app.services.llm.base import LLMAdapter
from app.services.llm.openai_compatible import OpenAICompatibleLLMAdapter
from app.services.llm.rule_based import RuleBasedLLMAdapter

OPENAI_BASE_URL = "https://api.openai.com/v1"


def create_llm_adapter(settings: Settings) -> LLMAdapter:
    if not settings.openai_api_key:
        return RuleBasedLLMAdapter()
    return OpenAICompatibleLLMAdapter(base_url=OPENAI_BASE_URL, api_key=settings.openai_api_key, model=settings.openai_model, timeout=settings.openai_timeout_seconds)
