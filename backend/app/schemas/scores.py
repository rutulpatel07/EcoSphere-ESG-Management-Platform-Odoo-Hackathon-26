"""Read models for department_scores and the org-level rollup."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DepartmentScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    period: str
    e_score: float
    s_score: float
    g_score: float
    total_score: float
    computed_at: datetime


class OrgScoreOut(BaseModel):
    period: str
    total: float
    e: float
    s: float
    g: float
    weights: dict[str, float]
