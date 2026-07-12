"""FastAPI dependencies for resolving the current user and guarding by role.

Other owner zones import ``get_current_user`` / ``require_role`` (or the
pre-built ``require_admin`` / ``require_manager`` helpers below) to protect
their own routes — this module is the single source of truth for "who is
calling and are they allowed to do this".
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db import get_db
from app.models import User
from app.models.enums import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_error

    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise credentials_error from exc

    raw_user_id = payload.get("sub")
    if raw_user_id is None:
        raise credentials_error

    user = db.get(User, int(raw_user_id))
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_role(*roles: UserRole) -> Callable[..., User]:
    """Build a dependency that only admits users whose role is in ``roles``."""

    def _guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return _guard


require_admin = require_role(UserRole.ADMIN)
require_manager = require_role(UserRole.ADMIN, UserRole.MANAGER)
require_employee = require_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.EMPLOYEE)
