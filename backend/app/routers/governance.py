"""Governance module: ESG policies, acknowledgements, audits, compliance
issues, and the append-only ESG ledger."""

from fastapi import APIRouter

router = APIRouter(prefix="/governance", tags=["governance"])


@router.get("/ping")
def ping() -> dict:
    return {"ok": True, "module": "governance"}
