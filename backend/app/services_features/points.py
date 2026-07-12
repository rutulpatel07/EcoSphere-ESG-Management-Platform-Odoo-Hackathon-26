"""Points ledger helpers.

A user's balance is always derived as ``SUM(point_transactions.points)``.
``users.points_balance`` is never read or written here — per instructions,
point_transactions is the single source of truth for balances.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_balance(db: Session, user_id: int) -> int:
    total = db.execute(
        text("SELECT COALESCE(SUM(points), 0) FROM point_transactions WHERE user_id = :user_id"),
        {"user_id": user_id},
    ).scalar_one()
    return int(total)


def award_points(
    db: Session,
    *,
    user_id: int,
    points: int,
    reason: str,
    ref_table: str,
    ref_id: int,
) -> None:
    """Insert a point_transactions delta row. Does not commit."""
    db.execute(
        text(
            """
            INSERT INTO point_transactions (user_id, points, reason, ref_table, ref_id)
            VALUES (:user_id, :points, :reason, :ref_table, :ref_id)
            """
        ),
        {
            "user_id": user_id,
            "points": points,
            "reason": reason,
            "ref_table": ref_table,
            "ref_id": ref_id,
        },
    )


def list_transactions(db: Session, user_id: int, limit: int = 50) -> list[dict]:
    rows = (
        db.execute(
            text(
                """
                SELECT id, points, reason, created_at
                FROM point_transactions
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"user_id": user_id, "limit": limit},
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows]
