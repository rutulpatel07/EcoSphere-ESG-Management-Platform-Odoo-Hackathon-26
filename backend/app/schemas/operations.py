"""Request/response shapes for operational records.

Output numeric fields are ``float`` so the JSON matches CONTRACT.md (which shows
plain numbers, e.g. ``"quantity": 1800``); inputs use ``Decimal`` so quantities
reach the carbon math without float rounding artifacts.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core import PydanticCustomError

from app.models.enums import OpType


class OperationalRecordCreate(BaseModel):
    op_type: OpType
    activity_type: str
    quantity: Decimal
    unit: str
    occurred_on: date
    department_id: int | None = None
    reference: str | None = None
    amount: Decimal | None = None

    @field_validator("activity_type", "unit")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise PydanticCustomError("blank", "This field must not be empty")
        return v

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise PydanticCustomError(
                "not_positive", "Quantity must be greater than 0"
            )
        return v


class OperationalRecordCreated(BaseModel):
    """201 response — mirrors CONTRACT.md exactly, including carbon_transaction_id."""

    id: int
    op_type: OpType
    activity_type: str
    quantity: float
    unit: str
    occurred_on: date
    carbon_transaction_id: int | None


class OperationalRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    op_type: OpType
    department_id: int | None
    activity_type: str
    quantity: float
    unit: str
    reference: str | None
    amount: float | None
    occurred_on: date
    created_by: int | None
    created_at: datetime
