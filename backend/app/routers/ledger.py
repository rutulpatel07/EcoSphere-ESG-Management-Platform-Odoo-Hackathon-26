"""ESG ledger — read-only, append-only (CONTRACT.md: /governance/ledger).

The ledger is never mutated through the API; entries are appended as a side
effect of domain writes (e.g. a carbon transaction). These endpoints only read
it back and verify the hash chain.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db import get_db
from app.models import ESGLedger, User
from app.schemas.ledger import LedgerEntryOut, LedgerVerifyResult
from app.services import ledger as ledger_service

router = APIRouter(prefix="/governance", tags=["ledger"])


@router.get("/ledger", response_model=list[LedgerEntryOut])
def list_ledger(
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ESGLedger]:
    stmt = select(ESGLedger).order_by(ESGLedger.seq.desc()).limit(limit)
    return list(db.scalars(stmt).all())


@router.get("/ledger/verify", response_model=LedgerVerifyResult)
def verify_ledger(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LedgerVerifyResult:
    result = ledger_service.load_and_verify(db)
    return LedgerVerifyResult(
        valid=result.valid,
        entries=result.entries,
        broken_at_seq=result.broken_at_seq,
    )
