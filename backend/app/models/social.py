"""Social domain tables (schema.sql sections 13, 14)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CSRActivity(Base):
    __tablename__ = "csr_activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL")
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL")
    )
    location: Mapped[str | None] = mapped_column(String(200))
    points_reward: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    capacity: Mapped[int | None] = mapped_column(Integer)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="OPEN")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EmployeeParticipation(Base):
    __tablename__ = "employee_participation"
    __table_args__ = (
        UniqueConstraint("csr_activity_id", "user_id", name="uq_employee_participation"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    csr_activity_id: Mapped[int] = mapped_column(
        ForeignKey("csr_activities.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    proof_url: Mapped[str | None] = mapped_column(String(400))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="REGISTERED")
    hours: Mapped[float | None] = mapped_column(Numeric(6, 2))
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
