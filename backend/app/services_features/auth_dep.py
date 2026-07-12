"""JWT auth dependency for the csr/challenges/gamification routers.

``app/routers/auth.py`` is still a ``/ping`` stub elsewhere in this codebase
(no token-issuing logic exists yet), and it is outside this owner zone. To
keep these routers functional against docs/CONTRACT.md's "Bearer JWT in
Authorization" rule without touching that file, this module independently
decodes the same HS256 shape using the already-shared ``app.config.settings``
(read-only) and the ``sub`` claim as the user id.
"""

from fastapi import Header, HTTPException, status
from jose import JWTError, jwt

from app.config import settings


def get_current_user_id(authorization: str | None = Header(default=None)) -> int:
    """Resolve the authenticated user's id from ``Authorization: Bearer <token>``."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    sub = payload.get("sub")
    try:
        return int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token subject")
