"""ESG scoring engine: per-department Environmental / Social / Governance
scores, the weighted department total, and the headcount-weighted org rollup.

The three formulas (given, not derived from schema.sql/CONTRACT.md, which only
define shapes) are::

    Env    = 0.6 * avg_goal_progress + 0.4 * (1 - min(1, co2e / budget))
    Social = 0.5 * participation_rate_per_capita + 0.5 * normalized_points_per_capita
    Gov    = 0.4 * ack_rate + 0.4 * (1 - overdue_ratio) + 0.2 * audit_completion

Every term above needs a concrete data source that isn't fully pinned down by
the schema. The choices made here, all made explicit in the helpers below:

- **avg_goal_progress**: mean of ``(current - baseline) / (target - baseline)``
  (baseline defaults to 0 when absent) over the department's own
  ``environmental_goals``, clamped per-goal to [0, 1]. A department with no
  goals of its own falls back to org-wide goals (``department_id IS NULL``).
  A department with *no* goals at all (not even org-wide ones) scores 1.0 for
  this term — there is no evidence of falling short, so it isn't penalized.
- **budget**: schema.sql has no explicit "carbon budget" column anywhere.
  We treat the department's (or org-wide fallback) environmental goal whose
  ``metric``/``unit`` mentions carbon/CO2/scope/GHG as the budget, using its
  ``target_value`` (tCO2e) as the ceiling. If none exists, the ratio term is
  1.0 (no known ceiling => no penalty) rather than undefined.
- **co2e**: summed ``carbon_transactions.co2e_kg`` for the department within
  the scoring period, converted to tonnes.
- **participation_rate_per_capita**: distinct CSR participants in the
  department during the period, divided by active headcount.
- **normalized_points_per_capita**: the department's positive
  ``point_transactions`` per capita during the period, min-max normalized
  against the *highest* points-per-capita among all departments in the same
  refresh batch (so the leading department scores 1.0 on this term).
- **ack_rate**: average, across the department's active users, of mandatory
  ``esg_policies`` acknowledged. No mandatory policies or no users => 1.0
  (vacuously compliant).
- **overdue_ratio**: of ``compliance_issues`` owned by the department's users,
  the fraction still OPEN/IN_PROGRESS past their ``due_date``. No issues => 0.
- **audit_completion**: audits have no department scoping in schema.sql (no
  ``department_id`` column), so this term is computed **organization-wide**
  and shared by every department's Gov score. No audits => 1.0.

Scores are stored 0-100 (matching the department_scores columns and
CONTRACT.md's dashboard examples); the formulas above are evaluated as
fractions in [0, 1] and multiplied by 100 at the end.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Audit,
    CarbonTransaction,
    ComplianceIssue,
    Department,
    DepartmentScore,
    EmployeeParticipation,
    EnvironmentalGoal,
    ESGPolicy,
    PointTransaction,
    PolicyAcknowledgement,
    Settings,
    User,
)
from app.services import events

DEFAULT_WEIGHTS = {"E": 40, "S": 30, "G": 30}
_BUDGET_KEYWORDS = ("co2", "carbon", "scope", "tco2e", "ghg", "emission")


# --------------------------------------------------------------------------
# Period helpers — "period" is a quarter string like "2026-Q3", matching the
# department_scores.period examples in CONTRACT.md ("2026-Q2").
# --------------------------------------------------------------------------


def current_period(ref: date | None = None) -> str:
    ref = ref or date.today()
    quarter = (ref.month - 1) // 3 + 1
    return f"{ref.year}-Q{quarter}"


def period_bounds(period: str) -> tuple[date, date]:
    """Inclusive [start, end] calendar dates for a "YYYY-Qn" period."""
    year_str, q_str = period.split("-Q")
    year, quarter = int(year_str), int(q_str)
    start_month = (quarter - 1) * 3 + 1
    start = date(year, start_month, 1)
    end_month, end_year = start_month + 2, year
    if end_month > 12:
        end_month -= 12
        end_year += 1
    end = (
        date(end_year, end_month + 1, 1) - timedelta(days=1)
        if end_month < 12
        else date(end_year, 12, 31)
    )
    return start, end


def _start_of_day(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=timezone.utc)


def _end_of_day(d: date) -> datetime:
    return datetime.combine(d, time.max, tzinfo=timezone.utc)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


# --------------------------------------------------------------------------
# Shared lookups
# --------------------------------------------------------------------------


def _headcount(db: Session, department_id: int) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.department_id == department_id, User.is_active.is_(True))
        )
        or 0
    )


def _get_weights(db: Session) -> dict[str, float]:
    row = db.get(Settings, 1)
    if row is None or not row.esg_weights:
        return dict(DEFAULT_WEIGHTS)
    return row.esg_weights


def _weighted_total(e: float, s: float, g: float, weights: dict[str, float]) -> float:
    we, ws, wg = weights.get("E", 40), weights.get("S", 30), weights.get("G", 30)
    denom = we + ws + wg
    if denom <= 0:
        we, ws, wg, denom = 40, 30, 30, 100
    total = (e * we + s * ws + g * wg) / denom
    return round(max(0.0, min(100.0, total)), 2)


# --------------------------------------------------------------------------
# Environmental
# --------------------------------------------------------------------------


def _goal_progress(goal: EnvironmentalGoal) -> float:
    if goal.target_value is None:
        return 0.0
    target = float(goal.target_value)
    baseline = float(goal.baseline_value) if goal.baseline_value is not None else 0.0
    current = float(goal.current_value) if goal.current_value is not None else 0.0
    if target == baseline:
        return 1.0 if current == target else 0.0
    return _clamp01((current - baseline) / (target - baseline))


def _goals_for_department(db: Session, department_id: int) -> list[EnvironmentalGoal]:
    own = list(
        db.scalars(
            select(EnvironmentalGoal).where(EnvironmentalGoal.department_id == department_id)
        ).all()
    )
    if own:
        return own
    return list(
        db.scalars(
            select(EnvironmentalGoal).where(EnvironmentalGoal.department_id.is_(None))
        ).all()
    )


def _find_budget_goal(goals: list[EnvironmentalGoal]) -> EnvironmentalGoal | None:
    candidates = [
        g
        for g in goals
        if g.target_value is not None
        and float(g.target_value) > 0
        and any(
            k in (g.metric or "").lower() or k in (g.unit or "").lower()
            for k in _BUDGET_KEYWORDS
        )
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda g: float(g.target_value))


def compute_environmental_score(db: Session, department_id: int, period: str) -> float:
    start, end = period_bounds(period)
    goals = _goals_for_department(db, department_id)
    avg_progress = (sum(_goal_progress(g) for g in goals) / len(goals)) if goals else 1.0

    budget_goal = _find_budget_goal(goals)
    co2e_kg = (
        db.scalar(
            select(func.coalesce(func.sum(CarbonTransaction.co2e_kg), 0)).where(
                CarbonTransaction.department_id == department_id,
                CarbonTransaction.occurred_on >= start,
                CarbonTransaction.occurred_on <= end,
            )
        )
        or 0
    )
    co2e_tonnes = float(co2e_kg) / 1000.0

    if budget_goal is None:
        ratio_term = 1.0
    else:
        budget_tonnes = float(budget_goal.target_value)
        ratio_term = _clamp01(1.0 - min(1.0, co2e_tonnes / budget_tonnes))

    fraction = 0.6 * avg_progress + 0.4 * ratio_term
    return round(_clamp01(fraction) * 100, 2)


# --------------------------------------------------------------------------
# Social
# --------------------------------------------------------------------------


def _points_per_capita(db: Session, department_id: int, start: date, end: date) -> float:
    headcount = _headcount(db, department_id)
    if headcount == 0:
        return 0.0
    dept_user_ids = select(User.id).where(
        User.department_id == department_id, User.is_active.is_(True)
    )
    points_sum = (
        db.scalar(
            select(func.coalesce(func.sum(PointTransaction.points), 0)).where(
                PointTransaction.user_id.in_(dept_user_ids),
                PointTransaction.points > 0,
                PointTransaction.created_at >= _start_of_day(start),
                PointTransaction.created_at <= _end_of_day(end),
            )
        )
        or 0
    )
    return float(points_sum) / headcount


def _max_points_per_capita(db: Session, period: str) -> float:
    start, end = period_bounds(period)
    department_ids = db.scalars(select(Department.id)).all()
    best = 0.0
    for dept_id in department_ids:
        best = max(best, _points_per_capita(db, dept_id, start, end))
    return best


def compute_social_score(
    db: Session, department_id: int, period: str, *, max_points_per_capita: float
) -> float:
    start, end = period_bounds(period)
    headcount = _headcount(db, department_id)
    if headcount == 0:
        return 0.0

    dept_user_ids = select(User.id).where(
        User.department_id == department_id, User.is_active.is_(True)
    )
    participants = (
        db.scalar(
            select(func.count(func.distinct(EmployeeParticipation.user_id))).where(
                EmployeeParticipation.user_id.in_(dept_user_ids),
                EmployeeParticipation.created_at >= _start_of_day(start),
                EmployeeParticipation.created_at <= _end_of_day(end),
            )
        )
        or 0
    )
    participation_rate = _clamp01(participants / headcount)

    points_per_capita = _points_per_capita(db, department_id, start, end)
    normalized_points = (
        _clamp01(points_per_capita / max_points_per_capita) if max_points_per_capita > 0 else 0.0
    )

    fraction = 0.5 * participation_rate + 0.5 * normalized_points
    return round(_clamp01(fraction) * 100, 2)


# --------------------------------------------------------------------------
# Governance
# --------------------------------------------------------------------------


def _audit_completion(db: Session) -> float:
    total = db.scalar(select(func.count()).select_from(Audit)) or 0
    if total == 0:
        return 1.0
    completed = (
        db.scalar(
            select(func.count()).select_from(Audit).where(Audit.status == "COMPLETED")
        )
        or 0
    )
    return _clamp01(completed / total)


def compute_governance_score(
    db: Session, department_id: int, period: str, *, audit_completion: float
) -> float:
    dept_user_ids = list(
        db.scalars(
            select(User.id).where(User.department_id == department_id, User.is_active.is_(True))
        ).all()
    )

    if not dept_user_ids:
        ack_rate = 1.0
        overdue_ratio = 0.0
    else:
        mandatory_policy_ids = list(
            db.scalars(select(ESGPolicy.id).where(ESGPolicy.is_mandatory.is_(True))).all()
        )
        if not mandatory_policy_ids:
            ack_rate = 1.0
        else:
            ack_count = (
                db.scalar(
                    select(func.count())
                    .select_from(PolicyAcknowledgement)
                    .where(
                        PolicyAcknowledgement.policy_id.in_(mandatory_policy_ids),
                        PolicyAcknowledgement.user_id.in_(dept_user_ids),
                    )
                )
                or 0
            )
            possible = len(mandatory_policy_ids) * len(dept_user_ids)
            ack_rate = _clamp01(ack_count / possible)

        today = date.today()
        issues = list(
            db.scalars(
                select(ComplianceIssue).where(ComplianceIssue.owner_user_id.in_(dept_user_ids))
            ).all()
        )
        if not issues:
            overdue_ratio = 0.0
        else:
            overdue = sum(
                1 for i in issues if i.status in ("OPEN", "IN_PROGRESS") and i.due_date < today
            )
            overdue_ratio = overdue / len(issues)

    fraction = 0.4 * ack_rate + 0.4 * (1 - overdue_ratio) + 0.2 * audit_completion
    return round(_clamp01(fraction) * 100, 2)


# --------------------------------------------------------------------------
# Refresh (writes department_scores) + org rollup
# --------------------------------------------------------------------------


def refresh_department_score(
    db: Session,
    department_id: int,
    period: str | None = None,
    *,
    weights: dict[str, float] | None = None,
    max_points_per_capita: float | None = None,
    audit_completion: float | None = None,
    publish: bool = True,
) -> DepartmentScore:
    """Recompute one department's E/S/G/total and upsert department_scores.

    Flushes but does not commit — the caller (a router, typically) owns the
    transaction. ``weights``/``max_points_per_capita``/``audit_completion`` can
    be precomputed once by ``refresh_all_department_scores`` to avoid redundant
    org-wide queries when refreshing every department in one batch.
    """
    period = period or current_period()
    weights = weights if weights is not None else _get_weights(db)
    max_ppc = (
        max_points_per_capita
        if max_points_per_capita is not None
        else _max_points_per_capita(db, period)
    )
    audit_comp = audit_completion if audit_completion is not None else _audit_completion(db)

    e = compute_environmental_score(db, department_id, period)
    s = compute_social_score(db, department_id, period, max_points_per_capita=max_ppc)
    g = compute_governance_score(db, department_id, period, audit_completion=audit_comp)
    total = _weighted_total(e, s, g, weights)

    row = db.scalar(
        select(DepartmentScore).where(
            DepartmentScore.department_id == department_id, DepartmentScore.period == period
        )
    )
    if row is None:
        row = DepartmentScore(department_id=department_id, period=period)
        db.add(row)

    row.e_score = e
    row.s_score = s
    row.g_score = g
    row.total_score = total
    row.computed_at = datetime.now(timezone.utc)
    db.flush()

    if publish:
        events.publish_score_updated(
            {
                "department_id": department_id,
                "period": period,
                "e": e,
                "s": s,
                "g": g,
                "total": total,
            }
        )
    return row


def refresh_all_department_scores(
    db: Session, period: str | None = None, *, publish: bool = True
) -> list[DepartmentScore]:
    """Recompute every department's score for ``period`` in one batch, sharing
    the org-wide lookups (weights, max points/capita, audit completion) so
    social-score normalization is consistent across departments."""
    period = period or current_period()
    weights = _get_weights(db)
    max_ppc = _max_points_per_capita(db, period)
    audit_comp = _audit_completion(db)

    department_ids = db.scalars(select(Department.id)).all()
    return [
        refresh_department_score(
            db,
            dept_id,
            period,
            weights=weights,
            max_points_per_capita=max_ppc,
            audit_completion=audit_comp,
            publish=publish,
        )
        for dept_id in department_ids
    ]


def reweight_department_scores(
    db: Session, period: str, weights: dict[str, float], *, publish: bool = True
) -> list[DepartmentScore]:
    """Re-derive total_score from already-cached e/s/g using new weights,
    without recomputing the underlying formulas. Used when settings.esg_weights
    changes — cheap, and keeps the cache honest immediately."""
    rows = list(
        db.scalars(select(DepartmentScore).where(DepartmentScore.period == period)).all()
    )
    for row in rows:
        row.total_score = _weighted_total(float(row.e_score), float(row.s_score), float(row.g_score), weights)
        row.computed_at = datetime.now(timezone.utc)
        if publish:
            events.publish_score_updated(
                {
                    "department_id": row.department_id,
                    "period": period,
                    "e": float(row.e_score),
                    "s": float(row.s_score),
                    "g": float(row.g_score),
                    "total": row.total_score,
                }
            )
    db.flush()
    return rows


def compute_org_score(db: Session, period: str | None = None) -> dict:
    """Headcount-weighted average of every cached department score for the
    period. Departments with zero headcount don't dilute the average (weight
    0); if literally no department has headcount, falls back to a plain
    (unweighted) average so the number isn't just 0."""
    period = period or current_period()
    weights = _get_weights(db)
    rows = list(db.scalars(select(DepartmentScore).where(DepartmentScore.period == period)).all())
    if not rows:
        return {"total": 0.0, "e": 0.0, "s": 0.0, "g": 0.0, "weights": weights, "period": period}

    total_headcount = 0
    sum_e = sum_s = sum_g = sum_total = 0.0
    for row in rows:
        hc = _headcount(db, row.department_id)
        total_headcount += hc
        sum_e += float(row.e_score) * hc
        sum_s += float(row.s_score) * hc
        sum_g += float(row.g_score) * hc
        sum_total += float(row.total_score) * hc

    if total_headcount == 0:
        n = len(rows)
        return {
            "total": round(sum(float(r.total_score) for r in rows) / n, 2),
            "e": round(sum(float(r.e_score) for r in rows) / n, 2),
            "s": round(sum(float(r.s_score) for r in rows) / n, 2),
            "g": round(sum(float(r.g_score) for r in rows) / n, 2),
            "weights": weights,
            "period": period,
        }

    return {
        "total": round(sum_total / total_headcount, 2),
        "e": round(sum_e / total_headcount, 2),
        "s": round(sum_s / total_headcount, 2),
        "g": round(sum_g / total_headcount, 2),
        "weights": weights,
        "period": period,
    }
