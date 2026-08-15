from fastapi import FastAPI
import uvicorn

from app.api.router import router
from app.core.config import get_settings


def create_app() -> FastAPI:
    app = FastAPI(title="Human Layer API")
    app.include_router(router)
    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    run()