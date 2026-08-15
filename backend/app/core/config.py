import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    environment: str
    host: str
    port: int


def get_settings() -> Settings:
    return Settings(
        environment=os.getenv("HUMAN_LAYER_ENV", "development"),
        host=os.getenv("HUMAN_LAYER_HOST", "127.0.0.1"),
        port=int(os.getenv("HUMAN_LAYER_PORT", "8000")),
    )


settings = get_settings()
