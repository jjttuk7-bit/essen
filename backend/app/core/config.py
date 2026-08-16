import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()
@dataclass(frozen=True)
class Settings:
    environment: str
    host: str
    port: int
    llm_provider: str = "rule_based"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    cors_origins: tuple[str, ...] = ()
def get_settings() -> Settings:
    return Settings(environment=os.getenv("HUMAN_LAYER_ENV", "development"), host=os.getenv("HUMAN_LAYER_HOST", "127.0.0.1"), port=int(os.getenv("HUMAN_LAYER_PORT", "8000")), llm_provider=os.getenv("HUMAN_LAYER_LLM_PROVIDER", "rule_based"), llm_base_url=os.getenv("HUMAN_LAYER_LLM_BASE_URL", ""), llm_api_key=os.getenv("HUMAN_LAYER_LLM_API_KEY", ""), llm_model=os.getenv("HUMAN_LAYER_LLM_MODEL", ""), cors_origins=tuple(origin.strip() for origin in os.getenv("HUMAN_LAYER_CORS_ORIGINS", "").split(",") if origin.strip()))
settings = get_settings()