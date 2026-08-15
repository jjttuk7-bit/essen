from fastapi import APIRouter

from app.api.documents import router as documents_router

router = APIRouter()
router.include_router(documents_router)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
