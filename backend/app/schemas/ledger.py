"""Read models for the ESG ledger and its verification result."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class LedgerEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seq: int
    entry_type: str
    ref_table: str | None
    ref_id: int | None
    payload: dict[str, Any]
    prev_hash: str | None
    row_hash: str
    actor_user_id: int | None
    created_at: datetime


class LedgerVerifyResult(BaseModel):
    """Shape mirrors CONTRACT.md: { valid, entries, broken_at_seq }."""

    valid: bool
    entries: int
    broken_at_seq: int | None
