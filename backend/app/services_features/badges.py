"""Badge engine: evaluates unlock_rule JSONB after every point delta.

unlock_rule shape: ``{"metric": "xp" | "challenges_completed", "op": ">=", "value": N}``

Auto-award is a runtime toggle read from ``settings.auto_award_badges`` (row
id=1) at call time, so an admin can turn it off via PATCH /settings without a
redeploy.
"""

import json
import operator

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services_features.notifications_service import TYPE_BADGE, create_notification
from app.services_features.points import get_balance

_OPS = {
    ">=": operator.ge,
    ">": operator.gt,
    "<=": operator.le,
    "<": operator.lt,
    "==": operator.eq,
    "!=": operator.ne,
}


def _metric_value(db: Session, user_id: int, metric: str) -> float | None:
    if metric == "xp":
        return get_balance(db, user_id)
    if metric == "challenges_completed":
        return db.execute(
            text(
                "SELECT COUNT(*) FROM challenge_participation "
                "WHERE user_id = :user_id AND status = 'COMPLETED'"
            ),
            {"user_id": user_id},
        ).scalar_one()
    return None


def _auto_award_enabled(db: Session) -> bool:
    value = db.execute(text("SELECT auto_award_badges FROM settings WHERE id = 1")).scalar()
    return True if value is None else bool(value)


def evaluate_badges(db: Session, user_id: int) -> list[dict]:
    """Award any newly-unlocked badges for user_id + notify. Does not commit."""
    if not _auto_award_enabled(db):
        return []

    candidates = (
        db.execute(
            text(
                """
                SELECT b.id, b.name, b.unlock_rule
                FROM badges b
                WHERE b.is_active = TRUE
                  AND NOT EXISTS (
                      SELECT 1 FROM user_badges ub
                      WHERE ub.user_id = :user_id AND ub.badge_id = b.id
                  )
                """
            ),
            {"user_id": user_id},
        )
        .mappings()
        .all()
    )

    awarded = []
    for badge in candidates:
        rule = badge["unlock_rule"] or {}
        if isinstance(rule, str):
            rule = json.loads(rule)
        metric, op, value = rule.get("metric"), rule.get("op"), rule.get("value")
        if metric is None or op not in _OPS or value is None:
            continue

        current = _metric_value(db, user_id, metric)
        if current is None or not _OPS[op](current, value):
            continue

        db.execute(
            text("INSERT INTO user_badges (user_id, badge_id) VALUES (:user_id, :badge_id)"),
            {"user_id": user_id, "badge_id": badge["id"]},
        )
        from app.services.ledger import append_entry

        append_entry(
            db,
            entry_type="BADGE",
            ref_table="user_badges",
            ref_id=badge["id"],
            actor_user_id=user_id,
            payload={"user_id": user_id, "badge_id": badge["id"]},
        )
        create_notification(
            db,
            user_id=user_id,
            title="Badge unlocked",
            body=f'You unlocked the "{badge["name"]}" badge.',
            type_=TYPE_BADGE,
            link="/gamification",
        )
        awarded.append(dict(badge))

    return awarded
