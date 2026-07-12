"""Carbon transaction read model + the recompute (factor-version diff) response."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.enums import DataTier


class CarbonTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operational_record_id: int | None
    emission_factor_id: int | None
    factor_value_used: float
    factor_version_used: int | None
    quantity: float
    co2e_kg: float
    scope: int | None
    data_tier: DataTier
    uncertainty_pct: float | None
    department_id: int | None
    occurred_on: date


class RecomputeTxnDelta(BaseModel):
    """Per-transaction diff of the snapshot factor against a target version."""

    transaction_id: int
    activity_type: str | None
    quantity: float
    factor_version_used: int | None
    factor_value_used: float
    new_factor_version: int
    new_factor_value: float | None
    old_co2e_kg: float
    new_co2e_kg: float
    delta_kg: float
    # methodology: a version-N factor exists and re-prices this txn;
    # none: version-N factor equals the snapshot; unavailable: no version-N factor.
    change_type: Literal["methodology", "none", "unavailable"]


class RecomputeResponse(BaseModel):
    factor_version: int
    transactions: list[RecomputeTxnDelta]
    total_old_co2e_kg: float
    total_new_co2e_kg: float
    total_delta_kg: float
    methodology_change_kg: float
    real_change_kg: float
    note: str
