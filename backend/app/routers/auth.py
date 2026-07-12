"""Authentication & session endpoints (login, refresh, current user)."""

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/ping")
def ping() -> dict:
    return {"ok": True, "module": "auth"}
