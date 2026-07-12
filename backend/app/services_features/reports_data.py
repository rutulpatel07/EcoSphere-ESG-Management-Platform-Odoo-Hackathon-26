"""Report data builders.

Four canned summary generators (env/social/gov/esg) matching
docs/CONTRACT.md's ``report_id`` shape, plus an additive cross-module
``custom_report`` (not documented in CONTRACT.md — kept as its own function
and endpoint rather than changing the documented /reports/generate shape).
"""

import re
from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

Columns = list[str]
Rows = list[dict]


def parse_period(period: str | None) -> tuple[date | None, date | None]:
    """Parse "YYYY", "YYYY-MM", or "YYYY-Qn" into an inclusive date range."""
    if not period:
        return None, None

    if m := re.fullmatch(r"(\d{4})-Q([1-4])", period):
        year, q = int(m.group(1)), int(m.group(2))
        start_month = (q - 1) * 3 + 1
        start = date(year, start_month, 1)
        end_month, end_year = start_month + 2, year
        if end_month == 12:
            end = date(end_year, 12, 31)
        else:
            end = date(end_year, end_month + 1, 1) - timedelta(days=1)
        return start, end

    if m := re.fullmatch(r"(\d{4})-(\d{2})", period):
        year, month = int(m.group(1)), int(m.group(2))
        start = date(year, month, 1)
        end = date(year, 12, 31) if month == 12 else date(year, month + 1, 1) - timedelta(days=1)
        return start, end

    if m := re.fullmatch(r"(\d{4})", period):
        year = int(m.group(1))
        return date(year, 1, 1), date(year, 12, 31)

    return None, None


# --------------------------------------------------------------------------
# The 4 canned summary generators
# --------------------------------------------------------------------------

def environmental_summary(db: Session, start: date | None, end: date | None) -> tuple[Columns, Rows]:
    columns = ["department", "scope", "data_tier", "total_co2e_kg", "record_count"]
    rows = db.execute(
        text(
            """
            SELECT COALESCE(d.name, 'Unassigned') AS department, ct.scope, ct.data_tier,
                   SUM(ct.co2e_kg) AS total_co2e_kg, COUNT(*) AS record_count
            FROM carbon_transactions ct
            LEFT JOIN departments d ON d.id = ct.department_id
            WHERE (:start IS NULL OR ct.occurred_on >= :start)
              AND (:end IS NULL OR ct.occurred_on <= :end)
            GROUP BY d.name, ct.scope, ct.data_tier
            ORDER BY total_co2e_kg DESC
            """
        ),
        {"start": start, "end": end},
    ).mappings().all()
    return columns, [dict(r) for r in rows]


def social_summary(db: Session, start: date | None, end: date | None) -> tuple[Columns, Rows]:
    columns = ["department", "activities_count", "participants_count", "verified_count", "total_hours"]
    rows = db.execute(
        text(
            """
            SELECT COALESCE(d.name, 'Unassigned') AS department,
                   COUNT(DISTINCT ca.id) AS activities_count,
                   COUNT(ep.id) AS participants_count,
                   COUNT(ep.id) FILTER (WHERE ep.status = 'VERIFIED') AS verified_count,
                   COALESCE(SUM(ep.hours), 0) AS total_hours
            FROM csr_activities ca
            LEFT JOIN departments d ON d.id = ca.department_id
            LEFT JOIN employee_participation ep ON ep.csr_activity_id = ca.id
            WHERE (:start IS NULL OR ca.start_date >= :start)
              AND (:end IS NULL OR ca.start_date <= :end)
            GROUP BY d.name
            ORDER BY department
            """
        ),
        {"start": start, "end": end},
    ).mappings().all()
    return columns, [dict(r) for r in rows]


def governance_summary(db: Session, start: date | None, end: date | None) -> tuple[Columns, Rows]:
    columns = ["title", "severity", "status", "owner", "due_date", "resolved_at"]
    rows = db.execute(
        text(
            """
            SELECT ci.title, ci.severity, ci.status, u.full_name AS owner,
                   ci.due_date, ci.resolved_at
            FROM compliance_issues ci
            LEFT JOIN users u ON u.id = ci.owner_user_id
            WHERE (:start IS NULL OR ci.due_date >= :start)
              AND (:end IS NULL OR ci.due_date <= :end)
            ORDER BY ci.due_date
            """
        ),
        {"start": start, "end": end},
    ).mappings().all()
    return columns, [dict(r) for r in rows]


def esg_summary(db: Session, start: date | None, end: date | None) -> tuple[Columns, Rows]:
    # department_scores is keyed by a period string (e.g. "2026-Q2"), not a
    # date column, so the start/end range isn't applied here.
    columns = ["department", "period", "e_score", "s_score", "g_score", "total_score"]
    rows = db.execute(
        text(
            """
            SELECT d.name AS department, ds.period, ds.e_score, ds.s_score, ds.g_score, ds.total_score
            FROM department_scores ds
            JOIN departments d ON d.id = ds.department_id
            ORDER BY ds.period DESC, ds.total_score DESC
            """
        )
    ).mappings().all()
    return columns, [dict(r) for r in rows]


REPORT_DEFINITIONS = {
    "environmental-summary": {"name": "Environmental Summary Report", "builder": environmental_summary},
    "social-summary": {"name": "Social Summary Report", "builder": social_summary},
    "governance-summary": {"name": "Governance Summary Report", "builder": governance_summary},
    "esg-summary": {"name": "ESG Summary Report", "builder": esg_summary},
}


# --------------------------------------------------------------------------
# Custom cross-module report (6 filters: department, date range, module,
# employee, challenge, esg_category)
# --------------------------------------------------------------------------

_MODULES = {"ENVIRONMENTAL", "SOCIAL", "GOVERNANCE", "GAMIFICATION"}
_ESG_CATEGORY_MODULES = {
    "E": {"ENVIRONMENTAL"},
    "S": {"SOCIAL", "GAMIFICATION"},
    "G": {"GOVERNANCE"},
}

_ENVIRONMENTAL_SQL = """
    SELECT 'ENVIRONMENTAL' AS module, orec.occurred_on AS date,
           COALESCE(d.name, 'Unassigned') AS department, u.full_name AS employee,
           orec.activity_type AS title,
           (orec.op_type || ' - ' || orec.quantity || ' ' || orec.unit) AS detail,
           'E' AS esg_category
    FROM operational_records orec
    LEFT JOIN departments d ON d.id = orec.department_id
    LEFT JOIN users u ON u.id = orec.created_by
    WHERE (:department_id IS NULL OR orec.department_id = :department_id)
      AND (:start_date IS NULL OR orec.occurred_on >= :start_date)
      AND (:end_date IS NULL OR orec.occurred_on <= :end_date)
      AND (:employee_id IS NULL OR orec.created_by = :employee_id)
"""

_SOCIAL_SQL = """
    SELECT 'SOCIAL' AS module, ca.start_date AS date,
           COALESCE(d.name, 'Unassigned') AS department, u.full_name AS employee,
           ca.title AS title, ('CSR participation: ' || ep.status) AS detail,
           'S' AS esg_category
    FROM employee_participation ep
    JOIN csr_activities ca ON ca.id = ep.csr_activity_id
    LEFT JOIN departments d ON d.id = ca.department_id
    LEFT JOIN users u ON u.id = ep.user_id
    WHERE (:department_id IS NULL OR ca.department_id = :department_id)
      AND (:start_date IS NULL OR ca.start_date >= :start_date)
      AND (:end_date IS NULL OR ca.start_date <= :end_date)
      AND (:employee_id IS NULL OR ep.user_id = :employee_id)
"""

# compliance_issues has no department_id column, so the department filter
# doesn't apply to this subquery — governance rows always ignore it.
_GOVERNANCE_SQL = """
    SELECT 'GOVERNANCE' AS module, ci.due_date AS date,
           CAST(NULL AS VARCHAR) AS department, u.full_name AS employee,
           ci.title AS title, ('Compliance: ' || ci.severity || '/' || ci.status) AS detail,
           'G' AS esg_category
    FROM compliance_issues ci
    LEFT JOIN users u ON u.id = ci.owner_user_id
    WHERE (:start_date IS NULL OR ci.due_date >= :start_date)
      AND (:end_date IS NULL OR ci.due_date <= :end_date)
      AND (:employee_id IS NULL OR ci.owner_user_id = :employee_id)
"""

_GAMIFICATION_SQL = """
    SELECT 'GAMIFICATION' AS module, c.start_date AS date,
           COALESCE(d.name, 'Unassigned') AS department, u.full_name AS employee,
           c.title AS title,
           ('Challenge: ' || cp.status || ' (progress ' || cp.progress || ')') AS detail,
           'S' AS esg_category
    FROM challenge_participation cp
    JOIN challenges c ON c.id = cp.challenge_id
    LEFT JOIN users u ON u.id = cp.user_id
    LEFT JOIN departments d ON d.id = u.department_id
    WHERE (:department_id IS NULL OR u.department_id = :department_id)
      AND (:start_date IS NULL OR c.start_date >= :start_date)
      AND (:end_date IS NULL OR c.start_date <= :end_date)
      AND (:employee_id IS NULL OR cp.user_id = :employee_id)
      AND (:challenge_id IS NULL OR cp.challenge_id = :challenge_id)
"""

_MODULE_SQL = {
    "ENVIRONMENTAL": _ENVIRONMENTAL_SQL,
    "SOCIAL": _SOCIAL_SQL,
    "GOVERNANCE": _GOVERNANCE_SQL,
    "GAMIFICATION": _GAMIFICATION_SQL,
}


def custom_report(
    db: Session,
    *,
    department_id: int | None,
    start_date: date | None,
    end_date: date | None,
    module: str | None,
    employee_id: int | None,
    challenge_id: int | None,
    esg_category: str | None,
) -> tuple[Columns, Rows]:
    columns = ["module", "date", "department", "employee", "title", "detail", "esg_category"]

    if module is not None and module not in _MODULES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown module: {module}")
    if esg_category is not None and esg_category not in _ESG_CATEGORY_MODULES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown esg_category: {esg_category}")

    if module:
        modules = {module}
    elif esg_category:
        modules = set(_ESG_CATEGORY_MODULES[esg_category])
    else:
        modules = set(_MODULES)

    if challenge_id is not None:
        modules &= {"GAMIFICATION"}

    subqueries = [_MODULE_SQL[m] for m in modules]
    if not subqueries:
        return columns, []

    query = " UNION ALL ".join(subqueries) + " ORDER BY date DESC NULLS LAST"
    rows = db.execute(
        text(query),
        {
            "department_id": department_id,
            "start_date": start_date,
            "end_date": end_date,
            "employee_id": employee_id,
            "challenge_id": challenge_id,
        },
    ).mappings().all()
    return columns, [dict(r) for r in rows]
