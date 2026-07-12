"""Reports module: ESG report generation (Excel/PDF) and exports."""

from fastapi import APIRouter

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/ping")
def ping() -> dict:
    return {"ok": True, "module": "reports"}
