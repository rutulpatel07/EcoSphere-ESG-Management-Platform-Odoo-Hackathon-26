"""Singleton platform settings (CONTRACT.md: /settings).

Reads are open to any authenticated user (the frontend needs the toggles to
gate UI). Only admins can PATCH -- it flips org-wide feature switches and the
ESG weighting that every department's total_score depends on. A weights
change re-derives total_score for every cached score in the *current* period
immediately (cheap: reuses already-computed e/s/g, see
``scoring.reweight_department_scores``) and publishes ``score.updated`` for
each, so the dashboard doesn't show a stale weighting until the next full
refresh.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.db import get_db
from app.models import Settings, User
from app.schemas.settings import SettingsOut, SettingsUpdate
from app.services import events, scoring

router = APIRouter(prefix="/settings", tags=["settings"])

_WEIGHTS_SUM_TOLERANCE = 1e-6


def _get_singleton(db: Session) -> Settings:
    row = db.get(Settings, 1)
    if row is None:
        # schema.sql seeds this row; a missing row means the DB wasn't
        # initialized from schema.sql -- surface that clearly rather than 500.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Settings row is missing -- has schema.sql been applied?",
        )
    return row


@router.get("", response_model=SettingsOut)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Settings:
    return _get_singleton(db)


@router.patch("", response_model=SettingsOut)
def update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Settings:
    row = _get_singleton(db)
    data = payload.model_dump(exclude_unset=True)

    new_weights = None
    if "esg_weights" in data:
        merged = {**row.esg_weights, **data.pop("esg_weights")}
        total = merged.get("E", 0) + merged.get("S", 0) + merged.get("G", 0)
        if abs(total - 100) > _WEIGHTS_SUM_TOLERANCE:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"esg_weights must sum to 100 (got {total})",
            )
        new_weights = merged
        row.esg_weights = merged

    for field, value in data.items():
        setattr(row, field, value)

    db.flush()
    score_rows = []
    if new_weights is not None:
        score_rows = scoring.reweight_department_scores(
            db, scoring.current_period(), new_weights, publish=False
        )

    db.commit()
    db.refresh(row)
    for score_row in score_rows:
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
    return row
