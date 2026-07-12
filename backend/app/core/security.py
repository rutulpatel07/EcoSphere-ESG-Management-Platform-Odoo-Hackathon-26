"""Password hashing (bcrypt) and JWT issuing/verification.

Hashing goes straight through the ``bcrypt`` package rather than
``passlib.CryptContext``: passlib 1.7.4 (the version pinned by the
``passlib[bcrypt]`` requirement) is unmaintained and its bcrypt backend probe
raises on bcrypt>=4.1's stricter 72-byte handling, breaking every hash/verify
call. ``bcrypt`` is already installed transitively via that same requirement,
so this does not add a new dependency -- it just talks to it directly.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(subject: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Raise ValueError on any invalid/expired token; callers turn that into a 401."""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
