"""Request/response shapes for /settings (CONTRACT.md).

``esg_weights`` values must sum to 100 — validated on the merged result
(existing weights overlaid with whatever subset the PATCH provides) in the
router, since a partial weights update like ``{"E": 50}`` alone can't be
checked in isolation.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core import PydanticCustomError


class ESGWeights(BaseModel):
    E: float
    S: float
    G: float

    @field_validator("E", "S", "G")
    @classmethod
    def nonneg(cls, v: float) -> float:
        if v < 0:
            raise PydanticCustomError("not_nonneg", "Weights must not be negative")
        return v


class SettingsUpdate(BaseModel):
    """PATCH accepts any subset of the four toggles and/or esg_weights."""

    gamification_enabled: bool | None = None
    csr_module_enabled: bool | None = None
    notifications_enabled: bool | None = None
    public_leaderboard: bool | None = None
    esg_weights: ESGWeights | None = None


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    gamification_enabled: bool
    csr_module_enabled: bool
    notifications_enabled: bool
    public_leaderboard: bool
    esg_weights: dict[str, float]
    updated_at: datetime
