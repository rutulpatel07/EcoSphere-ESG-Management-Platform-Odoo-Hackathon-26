"""Notifications module: user notifications feed and SSE stream."""

from fastapi import APIRouter

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/ping")
def ping() -> dict:
    return {"ok": True, "module": "notifications"}
