"""Dashboard aggregation endpoints (KPIs, ESG score, trends)."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db import get_db
from app.models import User
from app.services.scoring import compute_org_score, period_bounds

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/ping")
def ping() -> dict:
    return {"ok": True, "module": "dashboard"}


def _previous_period(period: str) -> str:
    year_str, q_str = period.split("-Q")
    year, quarter = int(year_str), int(q_str)
    return f"{year - 1}-Q4" if quarter == 1 else f"{year}-Q{quarter - 1}"


def _emissions_tonnes(db: Session, period: str) -> float:
    start, end = period_bounds(period)
    total = db.execute(
        text(
            "SELECT COALESCE(SUM(co2e_kg), 0) FROM carbon_transactions "
            "WHERE occurred_on >= :start AND occurred_on <= :end"
        ),
        {"start": start, "end": end},
    ).scalar()
    return float(total or 0) / 1000.0


def _participation_rate_pct(db: Session, period: str) -> float:
    start, end = period_bounds(period)
    headcount = db.execute(text("SELECT COUNT(*) FROM users WHERE is_active")).scalar() or 0
    if headcount == 0:
        return 0.0
    participants = db.execute(
        text(
            "SELECT COUNT(DISTINCT user_id) FROM employee_participation "
            "WHERE created_at::date >= :start AND created_at::date <= :end"
        ),
        {"start": start, "end": end},
    ).scalar() or 0
    return round(participants / headcount * 100, 1)


def _resolved_issues_count(db: Session, period: str) -> int:
    start, end = period_bounds(period)
    return db.execute(
        text(
            "SELECT COUNT(*) FROM compliance_issues "
            "WHERE resolved_at IS NOT NULL AND resolved_at::date >= :start AND resolved_at::date <= :end"
        ),
        {"start": start, "end": end},
    ).scalar() or 0


def _joined_challenges_count(db: Session, period: str) -> int:
    start, end = period_bounds(period)
    return db.execute(
        text(
            "SELECT COUNT(*) FROM challenge_participation "
            "WHERE created_at::date >= :start AND created_at::date <= :end"
        ),
        {"start": start, "end": end},
    ).scalar() or 0


def _pct_kpi(label: str, current: float, previous: float, *, unit: str = "", lower_is_better: bool) -> dict:
    value = f"{current:,.1f}{unit}"
    if previous <= 0:
        return {"label": label, "value": value, "delta": "New", "trend": "flat"}
    pct = (current - previous) / previous * 100
    if abs(pct) < 0.05:
        trend = "flat"
    elif pct > 0:
        trend = "down" if lower_is_better else "up"
    else:
        trend = "up" if lower_is_better else "down"
    return {"label": label, "value": value, "delta": f"{pct:+.1f}%", "trend": trend}


@router.get("/summary")
def summary(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    latest_period = db.execute(text("SELECT MAX(period) FROM department_scores")).scalar()
    org = compute_org_score(db, period=latest_period) if latest_period else compute_org_score(db)
    period = org["period"]
    previous_period = _previous_period(period)

    emissions = _emissions_tonnes(db, period)
    prev_emissions = _emissions_tonnes(db, previous_period)

    participation = _participation_rate_pct(db, period)
    prev_participation = _participation_rate_pct(db, previous_period)

    open_issues = db.execute(
        text("SELECT COUNT(*) FROM compliance_issues WHERE status IN ('OPEN', 'IN_PROGRESS')")
    ).scalar() or 0
    resolved_this_period = _resolved_issues_count(db, period)

    active_challenges = db.execute(
        text("SELECT COUNT(*) FROM challenges WHERE lifecycle = 'Active'")
    ).scalar() or 0
    joined_this_period = _joined_challenges_count(db, period)

    kpis = [
        _pct_kpi("Total Emissions (tCO2e)", emissions, prev_emissions, lower_is_better=True),
        _pct_kpi("CSR Participation", participation, prev_participation, unit="%", lower_is_better=False),
        {
            "label": "Open Compliance Issues",
            "value": str(open_issues),
            "delta": f"-{resolved_this_period}" if resolved_this_period else "0",
            "trend": "down" if resolved_this_period else "flat",
        },
        {
            "label": "Active Challenges",
            "value": str(active_challenges),
            "delta": f"+{joined_this_period}" if joined_this_period else "0",
            "trend": "up" if joined_this_period else "flat",
        },
    ]

    trend_rows = db.execute(
        text(
            """
            SELECT to_char(date_trunc('month', occurred_on), 'Mon') AS month,
                   date_trunc('month', occurred_on) AS month_start,
                   COALESCE(SUM(co2e_kg) FILTER (WHERE scope = 1), 0) AS scope1,
                   COALESCE(SUM(co2e_kg) FILTER (WHERE scope = 2), 0) AS scope2,
                   COALESCE(SUM(co2e_kg) FILTER (WHERE scope = 3), 0) AS scope3
            FROM carbon_transactions
            GROUP BY month_start, month
            ORDER BY month_start
            """
        )
    ).mappings().all()
    emissions_trend = [
        {
            "month": row["month"],
            "scope1": round(float(row["scope1"]) / 1000, 1),
            "scope2": round(float(row["scope2"]) / 1000, 1),
            "scope3": round(float(row["scope3"]) / 1000, 1),
        }
        for row in trend_rows
    ]

    dept_rows = db.execute(
        text(
            """
            SELECT d.name AS department, ds.period, ds.e_score AS e, ds.s_score AS s,
                   ds.g_score AS g, ds.total_score AS total
            FROM department_scores ds
            JOIN departments d ON d.id = ds.department_id
            WHERE ds.period = :period
            ORDER BY ds.total_score DESC
            """
        ),
        {"period": period},
    ).mappings().all()
    department_scores = [
        {
            "department": row["department"],
            "period": row["period"],
            "e": float(row["e"]),
            "s": float(row["s"]),
            "g": float(row["g"]),
            "total": float(row["total"]),
        }
        for row in dept_rows
    ]

    return {
        "esgScore": {
            "total": org["total"],
            "e": org["e"],
            "s": org["s"],
            "g": org["g"],
            "weights": org["weights"],
        },
        "kpis": kpis,
        "emissionsTrend": emissions_trend,
        "departmentScores": department_scores,
    }
