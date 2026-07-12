"""Notifications module: list + mark-read for the current user.

Insertion is done via services_features/notifications_service.create_notification,
called from this owner zone's own flows (APPROVAL from csr.py/challenges.py,
BADGE from services_features/badges.py). COMPLIANCE and POLICY notifications
are expected to be raised by the governance module reusing the same helper
— that module is outside this owner zone, so no trigger for those two types
is wired here; this router lists/reads whatever exists in the table
regardless of who inserted it.

SSE streaming (GET /notifications/stream) is not implemented in this pass —
only list + mark-read were requested.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.services_features.auth_dep import get_current_user_id

router = APIRouter(prefix="/notifications", tags=["notifications"])

NOTIFICATION_COLUMNS = "id, user_id, title, body, type, link, is_read, created_at"


@router.get("")
def list_notifications(
    unread: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
) -> list[dict]:
    query = f"SELECT {NOTIFICATION_COLUMNS} FROM notifications WHERE user_id = :user_id"
    params: dict = {"user_id": current_user_id}
    if unread:
        query += " AND is_read = FALSE"
    query += " ORDER BY created_at DESC"
    rows = db.execute(text(query), params).mappings().all()
    return [dict(row) for row in rows]


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    row = db.execute(
        text(
            "UPDATE notifications SET is_read = TRUE "
            "WHERE id = :id AND user_id = :user_id RETURNING id, is_read"
        ),
        {"id": notification_id, "user_id": current_user_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    db.commit()
    return dict(row)
