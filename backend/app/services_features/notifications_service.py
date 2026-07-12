"""Shared notification-creation helper and canonical type constants.

The 4 mandated notification types: COMPLIANCE (compliance issue raised),
APPROVAL (CSR/challenge participation approval decisions), POLICY (policy
reminders), BADGE (badge unlocks). APPROVAL and BADGE are wired from this
owner zone's own flows (csr.py, challenges.py, badges.py). COMPLIANCE and
POLICY originate in the governance module, which is outside this owner
zone — it is expected to reuse this same helper to raise them.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

TYPE_COMPLIANCE = "COMPLIANCE"
TYPE_APPROVAL = "APPROVAL"
TYPE_POLICY = "POLICY"
TYPE_BADGE = "BADGE"


def create_notification(
    db: Session,
    *,
    user_id: int,
    title: str,
    body: str | None,
    type_: str,
    link: str | None = None,
) -> None:
    """Insert a notification row. Does not commit."""
    db.execute(
        text(
            """
            INSERT INTO notifications (user_id, title, body, type, link)
            VALUES (:user_id, :title, :body, :type, :link)
            """
        ),
        {"user_id": user_id, "title": title, "body": body, "type": type_, "link": link},
    )
