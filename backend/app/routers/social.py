"""Social module: CSR activities, employee participation, categories."""

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_manager
from app.db import get_db
from app.models import User

router = APIRouter(prefix="/social", tags=["social"])

CATEGORY_COLUMNS = "id, name, type, description, icon, is_active"


@router.get("/ping")
def ping() -> dict:
    return {"ok": True, "module": "social"}


class CategoryCreate(BaseModel):
    name: str
    type: str
    description: str | None = None
    icon: str | None = None
    is_active: bool = True


@router.get("/categories")
def list_categories(
    type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[dict]:
    query = f"SELECT {CATEGORY_COLUMNS} FROM categories"
    params: dict = {}
    if type:
        query += " WHERE type = :type"
        params["type"] = type
    query += " ORDER BY id"
    rows = db.execute(text(query), params).mappings().all()
    return [dict(row) for row in rows]


@router.post("/categories", status_code=status.HTTP_201_CREATED)
def create_category(
    body: CategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
) -> dict:
    row = db.execute(
        text(
            f"""
            INSERT INTO categories (name, type, description, icon, is_active)
            VALUES (:name, :type, :description, :icon, :is_active)
            RETURNING {CATEGORY_COLUMNS}
            """
        ),
        body.model_dump(),
    ).mappings().first()
    db.commit()
    return dict(row)
