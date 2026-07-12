"""Gamification module: challenges, badges, rewards, point transactions,
redemptions, user badges, and the leaderboard."""

from fastapi import APIRouter

router = APIRouter(prefix="/gamification", tags=["gamification"])


@router.get("/ping")
def ping() -> dict:
    return {"ok": True, "module": "gamification"}
