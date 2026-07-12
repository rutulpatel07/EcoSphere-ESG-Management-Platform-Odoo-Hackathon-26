"""CSR module: activities, employee participation, and verification.

Routes are mounted under ``/social`` per docs/CONTRACT.md, even though this
file lives at routers/csr.py within the csr/challenges/gamification owner
zone — CONTRACT.md is authoritative for route shape, not module naming.
This router is not yet registered in app/main.py's ALL_ROUTERS (main.py is
outside this owner zone); see the final report for the one-line addition
needed there.
"""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.services_features.auth_dep import get_current_user_id
from app.services_features.evidence import EVIDENCE_REQUIRED
from app.services_features.notifications_service import TYPE_APPROVAL, create_notification
from app.services_features.points import award_points

router = APIRouter(prefix="/social", tags=["csr"])

ACTIVITY_COLUMNS = (
    "id, title, description, category_id, department_id, location, "
    "points_reward, capacity, start_date, end_date, status, created_by, created_at"
)
PARTICIPATION_COLUMNS = (
    "id, csr_activity_id, user_id, proof_url, status, hours, verified_by, verified_at, created_at"
)


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------

class ActivityCreate(BaseModel):
    title: str
    description: str | None = None
    category_id: int | None = None
    department_id: int | None = None
    location: str | None = None
    points_reward: int = 0
    capacity: int | None = None
    start_date: date
    end_date: date | None = None
    status: str = "OPEN"


class ActivityPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    category_id: int | None = None
    department_id: int | None = None
    location: str | None = None
    points_reward: int | None = None
    capacity: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None


class JoinRequest(BaseModel):
    proof_url: str | None = None


class ParticipationPatch(BaseModel):
    status: str | None = None
    hours: float | None = None
    proof_url: str | None = None


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _activity_or_404(db: Session, activity_id: int) -> dict:
    row = db.execute(
        text(f"SELECT {ACTIVITY_COLUMNS} FROM csr_activities WHERE id = :id"),
        {"id": activity_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "CSR activity not found")
    return dict(row)


def _participation_or_404(db: Session, participation_id: int) -> dict:
    row = db.execute(
        text(f"SELECT {PARTICIPATION_COLUMNS} FROM employee_participation WHERE id = :id"),
        {"id": participation_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Participation record not found")
    return dict(row)


# --------------------------------------------------------------------------
# Activities
# --------------------------------------------------------------------------

@router.get("/activities")
def list_activities(
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
) -> list[dict]:
    rows = db.execute(
        text(f"SELECT {ACTIVITY_COLUMNS} FROM csr_activities ORDER BY start_date DESC, id DESC")
    ).mappings().all()
    return [dict(row) for row in rows]


@router.post("/activities", status_code=status.HTTP_201_CREATED)
def create_activity(
    body: ActivityCreate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    row = db.execute(
        text(
            f"""
            INSERT INTO csr_activities
                (title, description, category_id, department_id, location,
                 points_reward, capacity, start_date, end_date, status, created_by)
            VALUES
                (:title, :description, :category_id, :department_id, :location,
                 :points_reward, :capacity, :start_date, :end_date, :status, :created_by)
            RETURNING {ACTIVITY_COLUMNS}
            """
        ),
        {**body.model_dump(), "created_by": current_user_id},
    ).mappings().first()
    db.commit()
    return dict(row)


@router.patch("/activities/{activity_id}")
def patch_activity(
    activity_id: int,
    body: ActivityPatch,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
) -> dict:
    activity = _activity_or_404(db, activity_id)
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return activity

    set_clause = ", ".join(f"{field} = :{field}" for field in updates)
    row = db.execute(
        text(f"UPDATE csr_activities SET {set_clause} WHERE id = :id RETURNING {ACTIVITY_COLUMNS}"),
        {**updates, "id": activity_id},
    ).mappings().first()
    db.commit()
    return dict(row)


# --------------------------------------------------------------------------
# Participation
# --------------------------------------------------------------------------

@router.get("/activities/{activity_id}/participants")
def list_participants(
    activity_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
) -> list[dict]:
    _activity_or_404(db, activity_id)
    rows = db.execute(
        text(
            f"SELECT {PARTICIPATION_COLUMNS} FROM employee_participation "
            "WHERE csr_activity_id = :id ORDER BY id"
        ),
        {"id": activity_id},
    ).mappings().all()
    return [dict(row) for row in rows]


@router.post("/activities/{activity_id}/join", status_code=status.HTTP_201_CREATED)
def join_activity(
    activity_id: int,
    body: JoinRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    _activity_or_404(db, activity_id)
    try:
        row = db.execute(
            text(
                f"""
                INSERT INTO employee_participation (csr_activity_id, user_id, proof_url, status)
                VALUES (:activity_id, :user_id, :proof_url, 'REGISTERED')
                RETURNING {PARTICIPATION_COLUMNS}
                """
            ),
            {"activity_id": activity_id, "user_id": current_user_id, "proof_url": body.proof_url},
        ).mappings().first()
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Already joined this activity")
    return dict(row)


@router.patch("/participation/{participation_id}")
def patch_participation(
    participation_id: int,
    body: ParticipationPatch,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    participation = _participation_or_404(db, participation_id)
    updates = body.model_dump(exclude_unset=True)

    final_proof_url = updates.get("proof_url", participation["proof_url"])
    requesting_verify = updates.get("status") == "VERIFIED"
    already_verified = participation["status"] == "VERIFIED"
    decision = updates.get("status") if updates.get("status") in ("VERIFIED", "REJECTED") else None

    if requesting_verify and EVIDENCE_REQUIRED and not final_proof_url:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Evidence required: proof_url must be set before this participation can be verified",
        )

    if decision:
        updates["verified_by"] = current_user_id
        updates["verified_at"] = datetime.now(timezone.utc)

    if not updates:
        return participation

    set_clause = ", ".join(f"{field} = :{field}" for field in updates)
    row = db.execute(
        text(
            f"UPDATE employee_participation SET {set_clause} WHERE id = :id "
            f"RETURNING {PARTICIPATION_COLUMNS}"
        ),
        {**updates, "id": participation_id},
    ).mappings().first()

    if decision:
        activity = _activity_or_404(db, participation["csr_activity_id"])
        create_notification(
            db,
            user_id=participation["user_id"],
            title=f"CSR participation {decision.lower()}",
            body=f'Your participation in "{activity["title"]}" was {decision.lower()}.',
            type_=TYPE_APPROVAL,
            link="/social",
        )
        if requesting_verify and not already_verified:
            award_points(
                db,
                user_id=participation["user_id"],
                points=activity["points_reward"],
                reason=f"CSR: {activity['title']}",
                ref_table="employee_participation",
                ref_id=participation_id,
            )

    db.commit()
    return dict(row)
