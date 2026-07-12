"""Environmental module: goals, operational records, carbon transactions,
emission factors, and product ESG profiles."""

from fastapi import APIRouter

router = APIRouter(prefix="/environmental", tags=["environmental"])


@router.get("/ping")
def ping() -> dict:
    return {"ok": True, "module": "environmental"}
