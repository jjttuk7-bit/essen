from app.core.config import Settings
from app.services.llm.base import LLMAdapter
from app.services.llm.openai_compatible import OpenAICompatibleLLMAdapter
from app.services.llm.rule_based import RuleBasedLLMAdapter


def create_llm_adapter(settings: Settings) -> LLMAdapter:
    if settings.llm_provider == "rule_based":
        return RuleBasedLLMAdapter()
    if settings.llm_provider == "openai_compatible":
        return OpenAICompatibleLLMAdapter(base_url=settings.llm_base_url, api_key=settings.llm_api_key, model=settings.llm_model)
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
