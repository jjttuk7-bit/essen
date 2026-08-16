import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
from app.api.router import router
from app.core.config import get_settings

logger = logging.getLogger("app")


class JSONErrorMiddleware(BaseHTTPMiddleware):
    """Turn unhandled errors into a JSON 500 that still passes through the CORS layer.

    Starlette's own 500 is produced outside every user middleware, so it carries no CORS
    headers. A browser then blocks the response and reports "Failed to fetch", hiding the
    actual failure. Answering here keeps the response inside the CORS layer.
    """

    async def dispatch(self, request, call_next):
        try:
            return await call_next(request)
        except Exception:
            logger.exception("Unhandled error for %s %s", request.method, request.url.path)
            return JSONResponse(status_code=500, content={"detail": "The server could not complete this request. Check the server logs for details."})


def create_app() -> FastAPI:
    app = FastAPI(title="Human Layer API")
    settings = get_settings()
    # Added before CORS so that CORS remains the outermost layer and stamps every response,
    # including the error responses produced above.
    app.add_middleware(JSONErrorMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=[settings.cors_origin] if settings.cors_origin else [], allow_credentials=False, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"])
    app.include_router(router)
    return app
app = create_app()
def run() -> None:
    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)
if __name__ == "__main__": run()
