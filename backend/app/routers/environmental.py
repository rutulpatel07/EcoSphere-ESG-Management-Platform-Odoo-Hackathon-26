"""Environmental admin surface: goals, emission factors, and the ESG score
cache (CONTRACT.md: /environmental/goals, /environmental/emission-factors;
scores endpoints are new, not in CONTRACT.md, but documented here).

Emission factors are strictly append-only: POST always inserts a new row,
never updates ``factor_value``/``version`` on an existing one (see
``create_emission_factor``). Goal and factor writes that can move a
department's ESG standing trigger an immediate score refresh so
department_scores never goes stale, and publish ``score.updated`` over SSE.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_manager
from app.db import get_db
from app.models import (
    Department,
    DepartmentScore,
    EmissionFactor,
    EnvironmentalGoal,
    ProductESGProfile,
    User,
)
from app.schemas.emission_factors import EmissionFactorCreate, EmissionFactorOut
from app.schemas.goals import GoalCreate, GoalOut, GoalUpdate
from app.schemas.products import ProductCreate, ProductOut
from app.schemas.scores import DepartmentScoreOut, OrgScoreOut
from app.services import events, scoring

router = APIRouter(prefix="/environmental", tags=["environmental"])


def _refresh_for_goal_change(db: Session, department_id: int | None) -> list[DepartmentScore]:
    """A department-scoped goal only moves that department's score; an
    org-wide goal (department_id is NULL) is a fallback for every department
    that has none of its own, so it can move any of them -- refresh all.

    Refreshes with publish=False: the caller commits first, then emits
    score.updated via _emit_score_events, so subscribers never observe an
    event for numbers that might still roll back.
    """
    if department_id is not None:
        return [scoring.refresh_department_score(db, department_id, publish=False)]
    return scoring.refresh_all_department_scores(db, publish=False)


def _emit_score_events(rows: list[DepartmentScore]) -> None:
    for row in rows:
        events.publish_score_updated(
            {
                "department_id": row.department_id,
                "period": row.period,
                "e": float(row.e_score),
                "s": float(row.s_score),
                "g": float(row.g_score),
                "total": float(row.total_score),
            }
        )


# --------------------------------------------------------------------------
# Environmental goals
# --------------------------------------------------------------------------


@router.get("/goals", response_model=list[GoalOut])
def list_goals(
    department_id: int | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EnvironmentalGoal]:
    stmt = select(EnvironmentalGoal)
    if department_id is not None:
        stmt = stmt.where(EnvironmentalGoal.department_id == department_id)
    if status_filter is not None:
        stmt = stmt.where(EnvironmentalGoal.status == status_filter)
    stmt = stmt.order_by(EnvironmentalGoal.target_date.asc())
    return list(db.scalars(stmt).all())


@router.post("/goals", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(
    payload: GoalCreate,
    db: Session = Depends(get_db),
    _manager: User = Depends(require_manager),
) -> EnvironmentalGoal:
    if payload.department_id is not None and db.get(Department, payload.department_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Department {payload.department_id} does not exist",
        )

    goal = EnvironmentalGoal(
        title=payload.title,
        description=payload.description,
        metric=payload.metric,
        baseline_value=payload.baseline_value,
        target_value=payload.target_value,
        unit=payload.unit,
        department_id=payload.department_id,
        start_date=payload.start_date,
        target_date=payload.target_date,
        status=payload.status,
    )
    db.add(goal)
    db.flush()
    score_rows = _refresh_for_goal_change(db, payload.department_id)
    db.commit()
    db.refresh(goal)
    _emit_score_events(score_rows)
    return goal


@router.patch("/goals/{goal_id}", response_model=GoalOut)
def update_goal(
    goal_id: int,
    payload: GoalUpdate,
    db: Session = Depends(get_db),
    _manager: User = Depends(require_manager),
) -> EnvironmentalGoal:
    goal = db.get(EnvironmentalGoal, goal_id)
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    data = payload.model_dump(exclude_unset=True)
    if "department_id" in data and data["department_id"] is not None:
        if db.get(Department, data["department_id"]) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Department {data['department_id']} does not exist",
            )

    old_department_id = goal.department_id
    for field, value in data.items():
        setattr(goal, field, value)
    db.flush()

    # Refresh whichever department(s) could have been affected: the goal's
    # department before AND after the edit (a department_id change moves the
    # goal out of one department's scoring and into another's).
    affected = {old_department_id, goal.department_id}
    score_rows: list[DepartmentScore] = []
    for dept_id in affected:
        score_rows.extend(_refresh_for_goal_change(db, dept_id))

    db.commit()
    db.refresh(goal)
    _emit_score_events(score_rows)
    return goal


# --------------------------------------------------------------------------
# Emission factors -- append-only: POST always inserts a new row
# --------------------------------------------------------------------------


@router.get("/emission-factors", response_model=list[EmissionFactorOut])
def list_emission_factors(
    activity_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EmissionFactor]:
    stmt = select(EmissionFactor)
    if activity_type is not None:
        stmt = stmt.where(EmissionFactor.activity_type == activity_type)
    stmt = stmt.order_by(EmissionFactor.activity_type.asc(), EmissionFactor.version.desc())
    return list(db.scalars(stmt).all())


@router.post(
    "/emission-factors", response_model=EmissionFactorOut, status_code=status.HTTP_201_CREATED
)
def create_emission_factor(
    payload: EmissionFactorCreate,
    db: Session = Depends(get_db),
    _manager: User = Depends(require_manager),
) -> EmissionFactor:
    version = payload.version
    if version is None:
        max_version = db.scalar(
            select(func.max(EmissionFactor.version)).where(
                EmissionFactor.activity_type == payload.activity_type
            )
        )
        version = (max_version or 0) + 1
    else:
        clash = db.scalar(
            select(EmissionFactor).where(
                EmissionFactor.activity_type == payload.activity_type,
                EmissionFactor.version == version,
            )
        )
        if clash is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Version {version} of '{payload.activity_type}' already exists "
                    "(new_version = new_row -- pick an unused version or omit it to auto-increment)"
                ),
            )

    # Close out the prior currently-open window for this activity+unit. This
    # only bounds valid_to on the OLD row -- factor_value/version on any
    # existing row are never touched, matching "never overwrite".
    open_row = db.scalar(
        select(EmissionFactor)
        .where(
            EmissionFactor.activity_type == payload.activity_type,
            EmissionFactor.unit == payload.unit,
            EmissionFactor.valid_to.is_(None),
            EmissionFactor.valid_from < payload.valid_from,
        )
        .order_by(EmissionFactor.version.desc())
        .limit(1)
    )
    if open_row is not None:
        open_row.valid_to = payload.valid_from - timedelta(days=1)

    factor = EmissionFactor(
        activity_type=payload.activity_type,
        unit=payload.unit,
        factor_value=payload.factor_value,
        source=payload.source,
        version=version,
        valid_from=payload.valid_from,
        valid_to=payload.valid_to,
        uncertainty_pct=payload.uncertainty_pct,
    )
    db.add(factor)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Version {version} of '{payload.activity_type}' already exists",
        ) from exc
    db.refresh(factor)
    return factor


# --------------------------------------------------------------------------
# ESG score cache (department_scores) -- read + on-demand refresh
# --------------------------------------------------------------------------


@router.get("/scores", response_model=list[DepartmentScoreOut])
def list_scores(
    period: str | None = Query(default=None),
    department_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    period = period or scoring.current_period()
    stmt = select(DepartmentScore).where(DepartmentScore.period == period)
    if department_id is not None:
        stmt = stmt.where(DepartmentScore.department_id == department_id)
    return list(db.scalars(stmt.order_by(DepartmentScore.department_id.asc())).all())


@router.get("/scores/org", response_model=OrgScoreOut)
def get_org_score(
    period: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrgScoreOut:
    result = scoring.compute_org_score(db, period)
    return OrgScoreOut(**result)


@router.post("/scores/refresh", response_model=list[DepartmentScoreOut])
def refresh_scores(
    period: str | None = Query(default=None),
    department_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _manager: User = Depends(require_manager),
):
    """On-demand recompute -- the same path relevant-event triggers use
    internally, exposed for a manual "refresh now" action."""
    period = period or scoring.current_period()
    if department_id is not None:
        if db.get(Department, department_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
            )
        rows = [scoring.refresh_department_score(db, department_id, period, publish=False)]
    else:
        rows = scoring.refresh_all_department_scores(db, period, publish=False)
    db.commit()
    for row in rows:
        db.refresh(row)
    _emit_score_events(rows)
    return rows


# --------------------------------------------------------------------------
# Product ESG profiles
# --------------------------------------------------------------------------


@router.get("/products", response_model=list[ProductOut])
def list_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProductESGProfile]:
    stmt = select(ProductESGProfile).order_by(ProductESGProfile.id.asc())
    return list(db.scalars(stmt).all())


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _manager: User = Depends(require_manager),
) -> ProductESGProfile:
    product = ProductESGProfile(**payload.model_dump())
    db.add(product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with sku '{payload.sku}' already exists",
        ) from exc
    db.refresh(product)
    return product
