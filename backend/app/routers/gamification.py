"""Gamification module: point balances (derived from point_transactions).

Challenges and challenge_participation live in routers/challenges.py
(same /gamification prefix). Badges, rewards/redemptions, and the
leaderboard are out of scope for this pass (not part of the requested
work) and remain unimplemented — see the final report.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.services_features.auth_dep import get_current_user_id
from app.services_features.points import get_balance, list_transactions

router = APIRouter(prefix="/gamification", tags=["gamification"])


@router.get("/users/{user_id}/points")
def get_points(
    user_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
) -> dict:
    return {
        "balance": get_balance(db, user_id),
        "transactions": list_transactions(db, user_id),
    }
