"""Append-only, hash-chained ESG ledger.

Each row's ``row_hash`` is::

    row_hash = SHA256( prev_hash + canonical_json(payload) )

where ``prev_hash`` is the previous row's ``row_hash`` (the empty string for the
genesis row). Payloads are stored using **JSON-native values only** — numbers
and dates are serialized to strings *before* they reach the ledger — so the
exact bytes hashed at write time are reproducible byte-for-byte when the chain
is re-read from JSONB during verification.

``append_entry`` deliberately does **not** commit: the caller owns the
transaction, which is what lets a carbon write (operational record + carbon
transaction + ledger entry) be atomic.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import ESGLedger

# Serializes concurrent ledger appends on Postgres so two transactions can never
# read the same "last row" and fork the chain. Transaction-scoped: auto-released
# on COMMIT/ROLLBACK. The integer is an arbitrary constant unique to the ledger.
_LEDGER_ADVISORY_LOCK_KEY = 4820043


def canonical_json(payload: dict[str, Any]) -> str:
    """Deterministic JSON encoding: sorted keys, no insignificant whitespace.

    ``payload`` must already consist of JSON-native types (str / int / bool /
    None / list / dict). Numbers-as-strings keep the hash stable across the
    JSONB round-trip.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_row_hash(prev_hash: str | None, payload: dict[str, Any]) -> str:
    """SHA-256 hex digest over ``prev_hash + canonical_json(payload)``."""
    material = (prev_hash or "") + canonical_json(payload)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class _LedgerRowLike(Protocol):
    """Structural type for anything ``verify_chain`` can walk (ORM row or stub)."""

    seq: int
    prev_hash: str | None
    row_hash: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class VerifyResult:
    valid: bool
    entries: int
    broken_at_seq: int | None


def verify_chain(rows: Iterable[_LedgerRowLike]) -> VerifyResult:
    """Walk rows **already ordered by ascending seq** and re-derive the chain.

    Returns the first break found (``valid=False`` with ``broken_at_seq``), or a
    clean result once every row's link and hash check out. Pure and
    DB-agnostic — it operates on any row exposing seq/prev_hash/row_hash/payload,
    which is what makes it unit-testable without a database.
    """
    prev_hash: str | None = None  # row_hash of the previous row (None before genesis)
    count = 0
    for row in rows:
        count += 1
        # Normalize a possibly-empty stored prev_hash to None for the link check.
        stored_prev = row.prev_hash or None
        if stored_prev != prev_hash:
            return VerifyResult(False, count, row.seq)
        if compute_row_hash(prev_hash, row.payload) != row.row_hash:
            return VerifyResult(False, count, row.seq)
        prev_hash = row.row_hash
    return VerifyResult(True, count, None)


def append_entry(
    db: Session,
    *,
    entry_type: str,
    payload: dict[str, Any],
    ref_table: str | None = None,
    ref_id: int | None = None,
    actor_user_id: int | None = None,
) -> ESGLedger:
    """Append one entry, linked to the current chain tip. Does not commit.

    ``payload`` must be JSON-native (see module docstring). The row is flushed so
    its ``seq`` is assigned, but the caller controls the surrounding transaction.
    """
    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(:k)"),
            {"k": _LEDGER_ADVISORY_LOCK_KEY},
        )

    last = db.scalar(select(ESGLedger).order_by(ESGLedger.seq.desc()).limit(1))
    prev_hash = last.row_hash if last is not None else None
    row_hash = compute_row_hash(prev_hash, payload)

    entry = ESGLedger(
        entry_type=entry_type,
        ref_table=ref_table,
        ref_id=ref_id,
        payload=payload,
        prev_hash=prev_hash,
        row_hash=row_hash,
        actor_user_id=actor_user_id,
    )
    db.add(entry)
    db.flush()
    return entry


def load_and_verify(db: Session) -> VerifyResult:
    """Load the entire chain ordered by seq and verify it."""
    rows = db.scalars(select(ESGLedger).order_by(ESGLedger.seq.asc())).all()
    return verify_chain(rows)
