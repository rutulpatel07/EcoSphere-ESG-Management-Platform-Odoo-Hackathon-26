"""Settings module: singleton platform settings, module toggles, ESG weights."""

from fastapi import APIRouter

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/ping")
def ping() -> dict:
    return {"ok": True, "module": "settings"}
