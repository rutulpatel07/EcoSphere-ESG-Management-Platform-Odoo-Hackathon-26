"""Carbon accounting: turn an operational record into a carbon transaction.

The whole point of this module is the *atomic* write described in CONTRACT.md —
"Posting a record triggers a matching carbon_transaction (factor snapshotted)".
``record_operation`` stages the operational record, the carbon transaction (with
the emission factor **snapshotted** at calc time), and the hash-chained ledger
entry within a single flush unit; the router wraps the whole thing in one commit
so a failure anywhere rolls all three back together.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import CarbonTransaction, EmissionFactor, OperationalRecord
from app.models.enums import DataTier, OpType
from app.services import ledger as ledger_service

# co2e_kg / factor snapshots are NUMERIC(18,6); quantize to the same scale so the
# value stored in the column and the value hashed into the ledger agree exactly.
_SCALE = Decimal("0.000001")

# GHG scope is not carried on the input tables, so it is derived from op_type.
# Heuristic and intentionally simple: direct combustion (fleet/manufacturing) is
# Scope 1; upstream purchased goods / spend is Scope 3.
_SCOPE_BY_OP_TYPE: dict[OpType, int] = {
    OpType.FLEET: 1,
    OpType.MANUFACTURING: 1,
    OpType.PURCHASE: 3,
    OpType.EXPENSE: 3,
}


@dataclass
class OperationInput:
    op_type: OpType
    activity_type: str
    quantity: Decimal
    unit: str
    occurred_on: date
    department_id: int | None = None
    reference: str | None = None
    amount: Decimal | None = None


def match_active_factor(
    db: Session, activity_type: str, unit: str, on_date: date
) -> EmissionFactor | None:
    """Best active emission factor for an activity on a date.

    Matches on (activity_type, unit) — the schema notes operational_records
    .activity_type "maps to emission_factors.activity_type" — restricted to
    factors whose validity window covers ``on_date`` (valid_to NULL = still
    valid), preferring the highest version.
    """
    stmt = (
        select(EmissionFactor)
        .where(
            EmissionFactor.activity_type == activity_type,
            EmissionFactor.unit == unit,
            EmissionFactor.valid_from <= on_date,
            or_(EmissionFactor.valid_to.is_(None), EmissionFactor.valid_to >= on_date),
        )
        .order_by(EmissionFactor.version.desc())
        .limit(1)
    )
    return db.scalar(stmt)


def record_operation(
    db: Session,
    data: OperationInput,
    *,
    actor_user_id: int | None,
    compute_emissions: bool = True,
) -> tuple[OperationalRecord, CarbonTransaction | None]:
    """Stage the operational record and (if a factor matches) the carbon
    transaction + ledger entry. Flushes but does not commit.

    When ``compute_emissions`` is False (settings.auto_emission_calc off), only
    the operational record is staged — no factor lookup, carbon transaction, or
    ledger entry.
    """
    record = OperationalRecord(
        op_type=data.op_type,
        department_id=data.department_id,
        activity_type=data.activity_type,
        quantity=data.quantity,
        unit=data.unit,
        reference=data.reference,
        amount=data.amount,
        occurred_on=data.occurred_on,
        created_by=actor_user_id,
    )
    db.add(record)
    db.flush()  # assign record.id

    if not compute_emissions:
        return record, None

    factor = match_active_factor(db, data.activity_type, data.unit, data.occurred_on)
    if factor is None:
        # No active factor: keep the operational record, but there is nothing to
        # snapshot, so no carbon transaction / ledger entry is created.
        return record, None

    quantity = Decimal(data.quantity)
    factor_value = Decimal(factor.factor_value)
    co2e_kg = (quantity * factor_value).quantize(_SCALE)
    scope = _SCOPE_BY_OP_TYPE.get(data.op_type)

    carbon = CarbonTransaction(
        operational_record_id=record.id,
        emission_factor_id=factor.id,
        factor_value_used=factor_value,
        factor_version_used=factor.version,
        quantity=quantity,
        co2e_kg=co2e_kg,
        scope=scope,
        data_tier=DataTier.CALCULATED,
        uncertainty_pct=factor.uncertainty_pct,
        department_id=data.department_id,
        occurred_on=data.occurred_on,
    )
    db.add(carbon)
    db.flush()  # assign carbon.id

    # JSON-native payload (numbers/dates as strings) for a stable ledger hash.
    payload = {
        "operational_record_id": record.id,
        "carbon_transaction_id": carbon.id,
        "emission_factor_id": factor.id,
        "op_type": data.op_type.value,
        "activity_type": data.activity_type,
        "quantity": str(quantity),
        "unit": data.unit,
        "factor_value_used": str(factor_value),
        "factor_version_used": factor.version,
        "co2e_kg": str(co2e_kg),
        "scope": scope,
        "data_tier": DataTier.CALCULATED.value,
        "department_id": data.department_id,
        "occurred_on": data.occurred_on.isoformat(),
    }
    ledger_service.append_entry(
        db,
        entry_type="CARBON",
        ref_table="carbon_transactions",
        ref_id=carbon.id,
        payload=payload,
        actor_user_id=actor_user_id,
    )

    return record, carbon
