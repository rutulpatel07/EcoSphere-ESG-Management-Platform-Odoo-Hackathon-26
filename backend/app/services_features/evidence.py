"""Evidence-requirement policy for participation approval endpoints.

Whether a proof_url is required before a CSR participation can be VERIFIED (or a
challenge participation COMPLETED) is a runtime toggle read from
``settings.evidence_required`` (row id=1) at call time, so an admin can change it
via PATCH /settings without a redeploy.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session


def evidence_required(db: Session) -> bool:
    value = db.execute(text("SELECT evidence_required FROM settings WHERE id = 1")).scalar()
    return True if value is None else bool(value)
