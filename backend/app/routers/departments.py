"""Department hierarchy endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("/ping")
def ping() -> dict:
    return {"ok": True, "module": "departments"}
