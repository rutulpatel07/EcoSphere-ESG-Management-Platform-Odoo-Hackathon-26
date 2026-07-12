"""Request/response shapes for /environmental/emission-factors (CONTRACT.md).

``version`` is optional on create: if omitted, the router auto-increments from
the highest existing version for that ``activity_type``. Either way, POST
always inserts a new row — never updates an existing one (see
app/routers/environmental.py).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from pydantic_core import PydanticCustomError


class EmissionFactorCreate(BaseModel):
    activity_type: str
    unit: str
    factor_value: float
    source: str | None = None
    version: int | None = None
    valid_from: date
    valid_to: date | None = None
    uncertainty_pct: float | None = None

    @field_validator("activity_type", "unit")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise PydanticCustomError("blank", "This field must not be empty")
        return v

    @field_validator("factor_value")
    @classmethod
    def factor_value_nonneg(cls, v: float) -> float:
        if v < 0:
            raise PydanticCustomError(
                "not_nonneg", "factor_value must not be negative"
            )
        return v

    @model_validator(mode="after")
    def valid_to_after_from(self) -> "EmissionFactorCreate":
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise PydanticCustomError(
                "invalid_range", "valid_to must not be before valid_from"
            )
        return self


class EmissionFactorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activity_type: str
    unit: str
    factor_value: float
    source: str | None
    version: int
    valid_from: date
    valid_to: date | None
    uncertainty_pct: float | None
