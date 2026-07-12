"""User & department administration endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/ping")
def ping() -> dict:
    return {"ok": True, "module": "users"}
