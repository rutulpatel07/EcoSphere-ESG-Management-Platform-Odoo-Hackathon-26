"""Department hierarchy endpoints (CONTRACT.md: /departments).

Reads are open to any authenticated user; structural mutations (create/patch/
delete) are admin-only since they reshape the org chart that headcount-based
scoring (app/services/scoring.py) and every other zone's department_id FKs
depend on.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.db import get_db
from app.models import Department, User
from app.schemas.departments import DepartmentCreate, DepartmentCreated, DepartmentOut, DepartmentUpdate

router = APIRouter(prefix="/departments", tags=["departments"])


def _validate_parent(db: Session, parent_id: int | None, *, self_id: int | None = None) -> None:
    if parent_id is None:
        return
    if self_id is not None and parent_id == self_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A department cannot be its own parent",
        )
    if db.get(Department, parent_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Parent department {parent_id} does not exist",
        )


def _validate_manager(db: Session, manager_id: int | None) -> None:
    if manager_id is None:
        return
    if db.get(User, manager_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"User {manager_id} does not exist",
        )


@router.get("", response_model=list[DepartmentOut])
def list_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Department]:
    return list(db.scalars(select(Department).order_by(Department.id.asc())).all())


@router.post("", response_model=DepartmentCreated, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Department:
    _validate_parent(db, payload.parent_id)
    _validate_manager(db, payload.manager_id)

    department = Department(
        name=payload.name,
        code=payload.code,
        parent_id=payload.parent_id,
        manager_id=payload.manager_id,
    )
    db.add(department)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Department code '{payload.code}' is already in use",
        ) from exc
    db.refresh(department)
    return department


@router.get("/{department_id}", response_model=DepartmentOut)
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Department:
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return department


@router.patch("/{department_id}", response_model=DepartmentOut)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Department:
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    data = payload.model_dump(exclude_unset=True)
    if "parent_id" in data:
        _validate_parent(db, data["parent_id"], self_id=department_id)
    if "manager_id" in data:
        _validate_manager(db, data["manager_id"])

    for field, value in data.items():
        setattr(department, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department code is already in use",
        ) from exc
    db.refresh(department)
    return department


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    db.delete(department)
    db.commit()
