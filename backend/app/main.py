from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.api.router import router
from app.core.config import get_settings
def create_app() -> FastAPI:
    app = FastAPI(title="Human Layer API")
    settings = get_settings()
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=False, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"])
    app.include_router(router)
    return app
app = create_app()
def run() -> None:
    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)
if __name__ == "__main__": run()