import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()
DEFAULT_OPENAI_MODEL = "gpt-5-mini"
@dataclass(frozen=True)
class Settings:
    environment: str
    host: str
    port: int
    openai_api_key: str = ""
    openai_model: str = DEFAULT_OPENAI_MODEL
    cors_origin: str = ""
def get_settings() -> Settings:
    return Settings(environment=os.getenv("HUMAN_LAYER_ENV", "development"), host=os.getenv("HUMAN_LAYER_HOST", "127.0.0.1"), port=int(os.getenv("HUMAN_LAYER_PORT", "8000")), openai_api_key=os.getenv("OPENAI_API_KEY", ""), openai_model=os.getenv("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL, cors_origin=os.getenv("CORS_ORIGIN", "").strip())
