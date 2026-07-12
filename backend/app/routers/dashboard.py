"""Dashboard aggregation endpoints (KPIs, ESG score, trends)."""

from fastapi import APIRouter

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/ping")
def ping() -> dict:
    return {"ok": True, "module": "dashboard"}
