"""Request/response shapes for /departments (CONTRACT.md)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core import PydanticCustomError


class DepartmentCreate(BaseModel):
    name: str
    code: str | None = None
    parent_id: int | None = None
    manager_id: int | None = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise PydanticCustomError("blank", "Department name must not be empty")
        return v

    @field_validator("code")
    @classmethod
    def code_not_blank(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None


class DepartmentUpdate(BaseModel):
    """PATCH accepts any subset."""

    name: str | None = None
    code: str | None = None
    parent_id: int | None = None
    manager_id: int | None = None


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str | None
    parent_id: int | None
    manager_id: int | None


class DepartmentCreated(DepartmentOut):
    created_at: datetime
