"""Request/response shapes for /environmental/goals (CONTRACT.md)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from pydantic_core import PydanticCustomError


class GoalCreate(BaseModel):
    title: str
    metric: str
    target_value: float
    description: str | None = None
    baseline_value: float | None = None
    unit: str | None = None
    department_id: int | None = None
    start_date: date
    target_date: date
    status: str = "ON_TRACK"

    @field_validator("title", "metric")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise PydanticCustomError("blank", "This field must not be empty")
        return v

    @model_validator(mode="after")
    def dates_ordered(self) -> "GoalCreate":
        if self.target_date < self.start_date:
            raise PydanticCustomError(
                "invalid_range", "target_date must not be before start_date"
            )
        return self


class GoalUpdate(BaseModel):
    """PATCH accepts any subset."""

    title: str | None = None
    description: str | None = None
    metric: str | None = None
    baseline_value: float | None = None
    target_value: float | None = None
    current_value: float | None = None
    unit: str | None = None
    department_id: int | None = None
    start_date: date | None = None
    target_date: date | None = None
    status: str | None = None


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    metric: str
    baseline_value: float | None
    target_value: float
    current_value: float
    unit: str | None
    department_id: int | None
    start_date: date
    target_date: date
    status: str
