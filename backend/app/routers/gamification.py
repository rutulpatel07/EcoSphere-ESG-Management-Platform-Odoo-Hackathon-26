"""Gamification module: points, badges, rewards/redemptions, leaderboard.

Challenges and challenge_participation live in routers/challenges.py (same
/gamification prefix).
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_manager
from app.db import get_db
from app.models import User
from app.models.enums import UserRole
from app.services_features.leaderboard import department_leaderboard, individual_leaderboard
from app.services_features.points import get_balance, list_transactions
from app.services_features.rewards import redeem as redeem_reward

router = APIRouter(prefix="/gamification", tags=["gamification"])


def _require_self_or_manager(current_user: User, user_id: int) -> None:
    """Allow access to another user's points/badges only for that user, or a
    manager/admin. Employees can only read their own."""
    if current_user.id != user_id and current_user.role not in (
        UserRole.ADMIN,
        UserRole.MANAGER,
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You may only view your own points and badges",
        )

BADGE_COLUMNS = "id, name, description, icon, tier, unlock_rule, points_value, is_active"
REWARD_COLUMNS = "id, name, description, cost_points, stock, image_url, is_active"
REDEMPTION_COLUMNS = "id, user_id, reward_id, points_spent, status, fulfilled_at, created_at"


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------

class BadgeCreate(BaseModel):
    name: str
    description: str | None = None
    icon: str | None = None
    tier: str | None = None
    unlock_rule: dict = {}
    points_value: int = 0
    is_active: bool = True


class RewardCreate(BaseModel):
    name: str
    description: str | None = None
    cost_points: int
    stock: int = 0
    image_url: str | None = None
    is_active: bool = True


# --------------------------------------------------------------------------
# Points
# --------------------------------------------------------------------------

@router.get("/users/{user_id}/points")
def get_points(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    _require_self_or_manager(current_user, user_id)
    return {
        "balance": get_balance(db, user_id),
        "transactions": list_transactions(db, user_id),
    }


# --------------------------------------------------------------------------
# Badges
# --------------------------------------------------------------------------

@router.get("/badges")
def list_badges(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[dict]:
    rows = db.execute(text(f"SELECT {BADGE_COLUMNS} FROM badges ORDER BY id")).mappings().all()
    return [dict(row) for row in rows]


@router.post("/badges", status_code=status.HTTP_201_CREATED)
def create_badge(
    body: BadgeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
) -> dict:
    row = db.execute(
        text(
            f"""
            INSERT INTO badges (name, description, icon, tier, unlock_rule, points_value, is_active)
            VALUES (:name, :description, :icon, :tier, :unlock_rule::jsonb, :points_value, :is_active)
            RETURNING {BADGE_COLUMNS}
            """
        ),
        {**body.model_dump(exclude={"unlock_rule"}), "unlock_rule": json.dumps(body.unlock_rule)},
    ).mappings().first()
    db.commit()
    return dict(row)


@router.get("/users/{user_id}/badges")
def list_user_badges(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    _require_self_or_manager(current_user, user_id)
    rows = db.execute(
        text(
            """
            SELECT b.id, b.name, b.description, b.icon, b.tier, b.unlock_rule,
                   b.points_value, b.is_active, ub.awarded_at
            FROM user_badges ub
            JOIN badges b ON b.id = ub.badge_id
            WHERE ub.user_id = :user_id
            ORDER BY ub.awarded_at DESC
            """
        ),
        {"user_id": user_id},
    ).mappings().all()
    return [dict(row) for row in rows]


# --------------------------------------------------------------------------
# Rewards & redemptions
# --------------------------------------------------------------------------

@router.get("/rewards")
def list_rewards(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[dict]:
    rows = db.execute(text(f"SELECT {REWARD_COLUMNS} FROM rewards ORDER BY id")).mappings().all()
    return [dict(row) for row in rows]


@router.post("/rewards", status_code=status.HTTP_201_CREATED)
def create_reward(
    body: RewardCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
) -> dict:
    row = db.execute(
        text(
            f"""
            INSERT INTO rewards (name, description, cost_points, stock, image_url, is_active)
            VALUES (:name, :description, :cost_points, :stock, :image_url, :is_active)
            RETURNING {REWARD_COLUMNS}
            """
        ),
        body.model_dump(),
    ).mappings().first()
    db.commit()
    return dict(row)


@router.post("/rewards/{reward_id}/redeem", status_code=status.HTTP_201_CREATED)
def redeem(
    reward_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return redeem_reward(db, user_id=current_user.id, reward_id=reward_id)


@router.get("/redemptions")
def list_redemptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    rows = db.execute(
        text(
            f"SELECT {REDEMPTION_COLUMNS} FROM reward_redemptions "
            "WHERE user_id = :user_id ORDER BY created_at DESC"
        ),
        {"user_id": current_user.id},
    ).mappings().all()
    return [dict(row) for row in rows]


# --------------------------------------------------------------------------
# Leaderboard
# --------------------------------------------------------------------------

@router.get("/leaderboard")
def leaderboard(
    scope: str = Query(default="individual", pattern="^(individual|department)$"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[dict]:
    if scope == "department":
        return department_leaderboard(db)
    return individual_leaderboard(db)
