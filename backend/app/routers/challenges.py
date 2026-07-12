"""Challenges module: full lifecycle, participation, progress, and XP award.

Routes are mounted under ``/gamification`` per docs/CONTRACT.md, alongside
routers/gamification.py (points). This router is not yet registered in
app/main.py's ALL_ROUTERS (main.py is outside this owner zone); see the
final report for the one-line addition needed there.
"""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_manager
from app.db import get_db
from app.models import User
from app.services import events, scoring
from app.services_features.evidence import evidence_required
from app.services_features.lifecycle import CHALLENGE_TRANSITIONS, is_legal_transition
from app.services_features.notifications_service import TYPE_APPROVAL, create_notification
from app.services_features.points import award_points

router = APIRouter(prefix="/gamification", tags=["challenges"])

CHALLENGE_COLUMNS = (
    "id, title, description, category_id, lifecycle, goal_metric, goal_target, "
    "points_reward, badge_id, start_date, end_date, created_by, created_at"
)
PARTICIPATION_COLUMNS = (
    "id, challenge_id, user_id, progress, status, proof_url, completed_at, created_at"
)


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------

class ChallengeCreate(BaseModel):
    title: str
    description: str | None = None
    category_id: int | None = None
    goal_metric: str | None = None
    goal_target: float | None = None
    points_reward: int = 0
    badge_id: int | None = None
    start_date: date
    end_date: date


class ChallengePatch(BaseModel):
    title: str | None = None
    description: str | None = None
    category_id: int | None = None
    lifecycle: str | None = None
    goal_metric: str | None = None
    goal_target: float | None = None
    points_reward: int | None = None
    badge_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None


class ChallengeParticipationPatch(BaseModel):
    progress: float | None = None
    status: str | None = None
    proof_url: str | None = None


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _challenge_or_404(db: Session, challenge_id: int) -> dict:
    row = db.execute(
        text(f"SELECT {CHALLENGE_COLUMNS} FROM challenges WHERE id = :id"),
        {"id": challenge_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Challenge not found")
    return dict(row)


def _participation_or_404(db: Session, participation_id: int) -> dict:
    row = db.execute(
        text(f"SELECT {PARTICIPATION_COLUMNS} FROM challenge_participation WHERE id = :id"),
        {"id": participation_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Challenge participation record not found")
    return dict(row)


# --------------------------------------------------------------------------
# Challenges
# --------------------------------------------------------------------------

@router.get("/challenges")
def list_challenges(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[dict]:
    rows = db.execute(
        text(f"SELECT {CHALLENGE_COLUMNS} FROM challenges ORDER BY start_date DESC, id DESC")
    ).mappings().all()
    return [dict(row) for row in rows]


@router.post("/challenges", status_code=status.HTTP_201_CREATED)
def create_challenge(
    body: ChallengeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
) -> dict:
    row = db.execute(
        text(
            f"""
            INSERT INTO challenges
                (title, description, category_id, lifecycle, goal_metric, goal_target,
                 points_reward, badge_id, start_date, end_date, created_by)
            VALUES
                (:title, :description, :category_id, 'Draft', :goal_metric, :goal_target,
                 :points_reward, :badge_id, :start_date, :end_date, :created_by)
            RETURNING {CHALLENGE_COLUMNS}
            """
        ),
        {**body.model_dump(), "created_by": current_user.id},
    ).mappings().first()
    db.commit()
    return dict(row)


@router.patch("/challenges/{challenge_id}")
def patch_challenge(
    challenge_id: int,
    body: ChallengePatch,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
) -> dict:
    challenge = _challenge_or_404(db, challenge_id)
    updates = body.model_dump(exclude_unset=True)

    if "lifecycle" in updates:
        current = challenge["lifecycle"]
        target = updates["lifecycle"]
        if not is_legal_transition(CHALLENGE_TRANSITIONS, current, target):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Illegal lifecycle transition: {current} -> {target}",
            )

    if not updates:
        return challenge

    set_clause = ", ".join(f"{field} = :{field}" for field in updates)
    row = db.execute(
        text(f"UPDATE challenges SET {set_clause} WHERE id = :id RETURNING {CHALLENGE_COLUMNS}"),
        {**updates, "id": challenge_id},
    ).mappings().first()
    db.commit()
    return dict(row)


# --------------------------------------------------------------------------
# Challenge participation
# --------------------------------------------------------------------------

@router.post("/challenges/{challenge_id}/join", status_code=status.HTTP_201_CREATED)
def join_challenge(
    challenge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    challenge = _challenge_or_404(db, challenge_id)
    if challenge["lifecycle"] != "Active":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Challenge is not open for joining")
    try:
        row = db.execute(
            text(
                f"""
                INSERT INTO challenge_participation (challenge_id, user_id, progress, status)
                VALUES (:challenge_id, :user_id, 0, 'JOINED')
                RETURNING {PARTICIPATION_COLUMNS}
                """
            ),
            {"challenge_id": challenge_id, "user_id": current_user.id},
        ).mappings().first()
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Already joined this challenge")
    return dict(row)


@router.patch("/challenge-participation/{participation_id}")
def patch_challenge_participation(
    participation_id: int,
    body: ChallengeParticipationPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
) -> dict:
    participation = _participation_or_404(db, participation_id)
    updates = body.model_dump(exclude_unset=True)

    final_proof_url = updates.get("proof_url", participation["proof_url"])
    requesting_complete = updates.get("status") == "COMPLETED"
    already_completed = participation["status"] == "COMPLETED"

    # No self-approval: a manager cannot approve/complete their own participation.
    if requesting_complete and current_user.id == participation["user_id"]:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You cannot approve your own challenge completion",
        )

    if requesting_complete and evidence_required(db) and not final_proof_url:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Evidence required: proof_url must be set before this challenge can be completed",
        )

    if requesting_complete and not already_completed:
        updates["completed_at"] = datetime.now(timezone.utc)

    if not updates:
        return participation

    set_clause = ", ".join(f"{field} = :{field}" for field in updates)
    row = db.execute(
        text(
            f"UPDATE challenge_participation SET {set_clause} WHERE id = :id "
            f"RETURNING {PARTICIPATION_COLUMNS}"
        ),
        {**updates, "id": participation_id},
    ).mappings().first()

    score_row = None
    if requesting_complete and not already_completed:
        challenge = _challenge_or_404(db, participation["challenge_id"])
        award_points(
            db,
            user_id=participation["user_id"],
            points=challenge["points_reward"],
            reason=f"Challenge: {challenge['title']}",
            ref_table="challenge_participation",
            ref_id=participation_id,
        )
        create_notification(
            db,
            user_id=participation["user_id"],
            title="Challenge completed",
            body=f'Your completion of "{challenge["title"]}" was approved.',
            type_=TYPE_APPROVAL,
            link="/gamification",
        )
        # Refresh the employee's department score in the same transaction so the
        # cache reflects the just-awarded points immediately.
        dept_id = db.execute(
            text("SELECT department_id FROM users WHERE id = :id"),
            {"id": participation["user_id"]},
        ).scalar()
        if dept_id is not None:
            score_row = scoring.refresh_department_score(db, dept_id, publish=False)

    db.commit()
    if score_row is not None:
        events.publish_score_updated(
            {
                "department_id": score_row.department_id,
                "period": score_row.period,
                "e": float(score_row.e_score),
                "s": float(score_row.s_score),
                "g": float(score_row.g_score),
                "total": float(score_row.total_score),
            }
        )
    return dict(row)
