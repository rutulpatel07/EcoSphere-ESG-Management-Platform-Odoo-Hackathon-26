"""Reward redemption as a single atomic transaction.

SELECT stock FOR UPDATE -> check stock -> check balance -> negative
point_transaction -> decrement stock -> redemption row. Any rejection
rolls back before any write happens, so a failed redemption never leaves a
partial point_transaction, stock decrement, or redemption row behind.
"""

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services_features.points import award_points, get_balance

REDEMPTION_COLUMNS = "id, user_id, reward_id, points_spent, status, fulfilled_at, created_at"


def redeem(db: Session, *, user_id: int, reward_id: int) -> dict:
    reward = (
        db.execute(
            text(
                "SELECT id, name, cost_points, stock, is_active FROM rewards "
                "WHERE id = :id FOR UPDATE"
            ),
            {"id": reward_id},
        )
        .mappings()
        .first()
    )

    if reward is None:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reward not found")
    if not reward["is_active"] or reward["stock"] <= 0:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Out of stock")

    balance = get_balance(db, user_id)
    if balance < reward["cost_points"]:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Insufficient points")

    award_points(
        db,
        user_id=user_id,
        points=-reward["cost_points"],
        reason=f"Redeem: {reward['name']}",
        ref_table="rewards",
        ref_id=reward_id,
    )
    db.execute(text("UPDATE rewards SET stock = stock - 1 WHERE id = :id"), {"id": reward_id})

    row = (
        db.execute(
            text(
                f"""
                INSERT INTO reward_redemptions (user_id, reward_id, points_spent, status)
                VALUES (:user_id, :reward_id, :points_spent, 'PENDING')
                RETURNING {REDEMPTION_COLUMNS}
                """
            ),
            {"user_id": user_id, "reward_id": reward_id, "points_spent": reward["cost_points"]},
        )
        .mappings()
        .first()
    )

    db.commit()
    return dict(row)
