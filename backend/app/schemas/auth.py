"""Request/response shapes for POST /auth/signup, /auth/login, /auth/me,
and the admin-only /auth/promote/{user_id} endpoint.

``email-validator`` is not in requirements.txt (dependencies are frozen), so
``pydantic.EmailStr`` is unavailable — email format is checked with a plain
regex instead. Validators raise ``PydanticCustomError`` rather than
``ValueError`` so the resulting 422 ``msg`` is the clean human-readable text
itself, without pydantic's default "Value error, " prefix.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core import PydanticCustomError

from app.models.enums import UserRole

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(value: str) -> str:
    value = value.strip()
    if not _EMAIL_RE.match(value):
        raise PydanticCustomError(
            "invalid_email",
            "Enter a valid email address, e.g. name@example.com",
        )
    return value.lower()


class SignupRequest(BaseModel):
    """No ``role`` field on purpose: signup always creates an EMPLOYEE."""

    email: str
    full_name: str
    password: str
    department_id: int | None = None

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return _validate_email(v)

    @field_validator("full_name")
    @classmethod
    def check_full_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise PydanticCustomError(
                "too_short", "Full name must be at least 2 characters long"
            )
        return v

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        if len(v) < 8:
            raise PydanticCustomError(
                "too_short", "Password must be at least 8 characters long"
            )
        if len(v.encode("utf-8")) > 72:
            raise PydanticCustomError(
                "too_long", "Password must be at most 72 bytes long"
            )
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return _validate_email(v)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole
    department_id: int | None
    points_balance: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class PromoteRequest(BaseModel):
    role: UserRole
