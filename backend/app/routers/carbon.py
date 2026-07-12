"""Carbon transactions, factor-version recompute, and the SSE event stream.

Recompute (CONTRACT.md has no shape for this, so it is designed here) re-prices
every carbon transaction against a target emission-factor version and splits the
movement into a *methodology* change (the factor value changed) versus a *real*
change (activity/quantity changed). Because a recompute holds quantities
constant, the real component is 0 by construction — reported explicitly so the
zero is understood as a property of the operation, not a bug.
"""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.deps import get_current_user, require_manager
from app.db import get_db
from app.models import CarbonTransaction, EmissionFactor, User
from app.schemas.carbon import CarbonTransactionOut, RecomputeResponse, RecomputeTxnDelta
from app.services import events

router = APIRouter(prefix="/environmental", tags=["carbon"])

_SCALE = Decimal("0.000001")
_RECOMPUTE_NOTE = (
    "Recompute holds activity quantities constant, so the entire movement is a "
    "methodology change (new emission-factor version); the real (activity) "
    "change is 0 by construction. Transactions with no factor at the requested "
    "version are left unchanged (change_type=unavailable)."
)


@router.get("/carbon-transactions", response_model=list[CarbonTransactionOut])
def list_carbon_transactions(
    department_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CarbonTransaction]:
    stmt = select(CarbonTransaction)
    if department_id is not None:
        stmt = stmt.where(CarbonTransaction.department_id == department_id)
    stmt = stmt.order_by(CarbonTransaction.occurred_on.desc(), CarbonTransaction.id.desc())
    return list(db.scalars(stmt).all())


@router.post("/carbon-transactions/recompute", response_model=RecomputeResponse)
def recompute(
    factor_version: int = Query(..., description="Emission factor version to re-price against"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
) -> RecomputeResponse:
    txns = db.scalars(select(CarbonTransaction)).all()

    deltas: list[RecomputeTxnDelta] = []
    total_old = Decimal(0)
    total_new = Decimal(0)
    methodology = Decimal(0)

    for txn in txns:
        old_co2e = Decimal(txn.co2e_kg)
        activity_type: str | None = None
        new_factor: EmissionFactor | None = None

        if txn.emission_factor_id is not None:
            snapshot_factor = db.get(EmissionFactor, txn.emission_factor_id)
            if snapshot_factor is not None:
                activity_type = snapshot_factor.activity_type
                new_factor = db.scalar(
                    select(EmissionFactor).where(
                        EmissionFactor.activity_type == activity_type,
                        EmissionFactor.version == factor_version,
                    )
                )

        if new_factor is not None:
            new_value = Decimal(new_factor.factor_value)
            new_co2e = (Decimal(txn.quantity) * new_value).quantize(_SCALE)
            change_type = "methodology" if new_value != Decimal(txn.factor_value_used) else "none"
            methodology += new_co2e - old_co2e
        else:
            new_value = None
            new_co2e = old_co2e
            change_type = "unavailable"

        total_old += old_co2e
        total_new += new_co2e
        deltas.append(
            RecomputeTxnDelta(
                transaction_id=txn.id,
                activity_type=activity_type,
                quantity=float(txn.quantity),
                factor_version_used=txn.factor_version_used,
                factor_value_used=float(txn.factor_value_used),
                new_factor_version=factor_version,
                new_factor_value=float(new_value) if new_value is not None else None,
                old_co2e_kg=float(old_co2e),
                new_co2e_kg=float(new_co2e),
                delta_kg=float(new_co2e - old_co2e),
                change_type=change_type,
            )
        )

    total_delta = total_new - total_old
    real_change = total_delta - methodology  # 0 by construction; reported for auditability

    return RecomputeResponse(
        factor_version=factor_version,
        transactions=deltas,
        total_old_co2e_kg=float(total_old),
        total_new_co2e_kg=float(total_new),
        total_delta_kg=float(total_delta),
        methodology_change_kg=float(methodology),
        real_change_kg=float(real_change),
        note=_RECOMPUTE_NOTE,
    )


@router.get("/events")
async def stream_events(request: Request) -> EventSourceResponse:
    """SSE stream of ``carbon.created`` and ``score.updated`` events.

    Left unauthenticated because browser ``EventSource`` cannot attach an
    Authorization header; payloads carry only non-sensitive ids/metrics.
    """
    events.bind_loop(asyncio.get_running_loop())
    queue = await events.subscribe()

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "{}"}
                    continue
                yield {"event": message["event"], "data": json.dumps(message["data"])}
        finally:
            events.unsubscribe(queue)

    return EventSourceResponse(event_generator())
