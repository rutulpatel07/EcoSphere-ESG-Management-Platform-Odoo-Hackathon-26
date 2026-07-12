"""Points ledger helpers.

A user's balance is always derived as ``SUM(point_transactions.points)``.
``users.points_balance`` is never read or written here — per instructions,
point_transactions is the single source of truth for balances.
"""

# NOTE: app.services_features.badges imports get_balance from this module,
# so evaluate_badges is imported lazily inside award_points to avoid a
# circular import at module load time.

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
    """Insert a point_transactions delta row, ledger it, and re-evaluate badges.

    Does not commit — the caller owns the transaction, so the point delta, the
    POINTS ledger entry, and any badge unlocks all land (or roll back) together.
    """
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

    # Ledger the points movement (covers both earns and reward-redemption spends,
    # which flow through here with a negative delta). Small payload: ids + delta.
    from app.services.ledger import append_entry

    append_entry(
        db,
        entry_type="POINTS",
        ref_table=ref_table,
        ref_id=ref_id,
        actor_user_id=user_id,
        payload={"user_id": user_id, "delta": points, "reason": reason},
    )

    from app.services_features.badges import evaluate_badges

    evaluate_badges(db, user_id)


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
