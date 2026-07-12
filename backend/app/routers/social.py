"""Social module: CSR activities, employee participation, categories."""

from fastapi import APIRouter

router = APIRouter(prefix="/social", tags=["social"])


@router.get("/ping")
def ping() -> dict:
    return {"ok": True, "module": "social"}
