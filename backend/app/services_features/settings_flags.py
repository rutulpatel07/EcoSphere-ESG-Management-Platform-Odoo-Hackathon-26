"""Call-time readers for the singleton ``settings`` row (id=1) feature toggles.

Kept tiny and side-effect-free so any flow can consult a flag without importing
the settings router. Each reader defaults to the schema default (TRUE) when the
row/column is somehow absent, so a misconfigured DB fails open rather than
silently disabling a whole subsystem.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session


def notifications_enabled(db: Session) -> bool:
    value = db.execute(text("SELECT notifications_enabled FROM settings WHERE id = 1")).scalar()
    return True if value is None else bool(value)
