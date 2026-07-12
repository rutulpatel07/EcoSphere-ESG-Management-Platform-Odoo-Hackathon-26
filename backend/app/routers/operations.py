"""Operational records (CONTRACT.md: /environmental/operational-records).

Posting a record is the entry point for carbon accounting: it writes the record
and, when an active emission factor matches, a snapshotted carbon transaction and
a hash-chained ledger entry — all in one transaction — then emits ``carbon.created``
on the SSE bus.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db import get_db
from app.models import Department, OperationalRecord, User
from app.models.enums import OpType
from app.schemas.operations import (
    OperationalRecordCreate,
    OperationalRecordCreated,
    OperationalRecordOut,
)
from app.services import emissions, events, scoring
from app.services.emissions import OperationInput

router = APIRouter(prefix="/environmental", tags=["operations"])


@router.post(
    "/operational-records",
    response_model=OperationalRecordCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_operational_record(
    payload: OperationalRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OperationalRecordCreated:
    if payload.department_id is not None and db.get(Department, payload.department_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Department {payload.department_id} does not exist",
        )

    data = OperationInput(
        op_type=payload.op_type,
        activity_type=payload.activity_type,
        quantity=payload.quantity,
        unit=payload.unit,
        occurred_on=payload.occurred_on,
        department_id=payload.department_id,
        reference=payload.reference,
        amount=payload.amount,
    )

    score_row = None
    try:
        record, carbon = emissions.record_operation(db, data, actor_user_id=current_user.id)
        # A new carbon transaction can move the department's E score (and, via
        # points/participation elsewhere, S/G too) -- refresh in the SAME
        # transaction so the cache never observably lags the data it's derived
        # from. publish=False: the event fires after commit below, once the
        # numbers are actually durable.
        if carbon is not None and record.department_id is not None:
            score_row = scoring.refresh_department_score(
                db, record.department_id, publish=False
            )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(record)
    if carbon is not None:
        db.refresh(carbon)
        # Emit only after the commit so subscribers never see uncommitted data.
        events.publish_carbon_created(
            {
                "carbon_transaction_id": carbon.id,
                "operational_record_id": record.id,
                "co2e_kg": float(carbon.co2e_kg),
                "scope": carbon.scope,
                "department_id": carbon.department_id,
                "occurred_on": carbon.occurred_on.isoformat(),
            }
        )
    if score_row is not None:
        events.publish_score_updated(
            {
                "department_id": score_row.department_id,
                "period": score_row.period,
                "e": float(score_row.e_score),
                "s": float(score_row.s_score),
                "g": float(score_row.g_score),
                "total": float(score_row.total_score),
            }
        )

    return OperationalRecordCreated(
        id=record.id,
        op_type=record.op_type,
        activity_type=record.activity_type,
        quantity=float(record.quantity),
        unit=record.unit,
        occurred_on=record.occurred_on,
        carbon_transaction_id=carbon.id if carbon is not None else None,
    )


@router.get("/operational-records", response_model=list[OperationalRecordOut])
def list_operational_records(
    op_type: OpType | None = Query(default=None),
    department_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OperationalRecord]:
    stmt = select(OperationalRecord)
    if op_type is not None:
        stmt = stmt.where(OperationalRecord.op_type == op_type)
    if department_id is not None:
        stmt = stmt.where(OperationalRecord.department_id == department_id)
    stmt = stmt.order_by(OperationalRecord.occurred_on.desc(), OperationalRecord.id.desc())
    return list(db.scalars(stmt).all())
