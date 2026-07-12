"""Background jobs (APScheduler).

Currently one job: an hourly sweep that flags OPEN/IN_PROGRESS
``compliance_issues`` past their ``due_date`` by inserting a ``notifications``
row for the issue's owner. Notifying is idempotent per (owner, issue) --
a standing overdue issue is flagged once, not re-flagged every hour until it's
resolved -- checked via the ``link`` field, which encodes the issue id.

Runs on a classic ``BackgroundScheduler`` (its own thread), not
``AsyncIOScheduler``: the job body does blocking SQLAlchemy work, and a
thread-based scheduler keeps that off the FastAPI event loop without needing
an async DB driver.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.db import SessionLocal
from app.models import ComplianceIssue, Notification

logger = logging.getLogger(__name__)

_OVERDUE_STATUSES = ("OPEN", "IN_PROGRESS")
_JOB_ID = "flag_overdue_compliance_issues"


def _link_for(issue_id: int) -> str:
    return f"/governance/compliance-issues/{issue_id}"


def flag_overdue_compliance_issues() -> int:
    """One sweep. Returns the count of notifications created (used by tests
    and logged here so the job's effect is visible without a debugger)."""
    db = SessionLocal()
    try:
        today = date.today()
        overdue = db.scalars(
            select(ComplianceIssue).where(
                ComplianceIssue.status.in_(_OVERDUE_STATUSES),
                ComplianceIssue.due_date < today,
            )
        ).all()

        created = 0
        for issue in overdue:
            link = _link_for(issue.id)
            already_notified = db.scalar(
                select(Notification.id)
                .where(
                    Notification.user_id == issue.owner_user_id,
                    Notification.link == link,
                    Notification.type == "COMPLIANCE",
                )
                .limit(1)
            )
            if already_notified is not None:
                continue

            db.add(
                Notification(
                    user_id=issue.owner_user_id,
                    title="Compliance issue overdue",
                    body=(
                        f'"{issue.title}" was due {issue.due_date.isoformat()} '
                        f"and is still {issue.status}."
                    ),
                    type="COMPLIANCE",
                    link=link,
                )
            )
            created += 1

        db.commit()
        if created:
            logger.info("flag_overdue_compliance_issues: created %d notification(s)", created)
        return created
    finally:
        db.close()


_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> BackgroundScheduler:
    """Start the background scheduler (idempotent). Fires once immediately on
    startup (so overdue issues surface right away, not up to an hour later)
    and then every hour."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        flag_overdue_compliance_issues,
        trigger="interval",
        hours=1,
        id=_JOB_ID,
        next_run_time=datetime.now(timezone.utc),
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("scheduler started: %s runs hourly", _JOB_ID)
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
