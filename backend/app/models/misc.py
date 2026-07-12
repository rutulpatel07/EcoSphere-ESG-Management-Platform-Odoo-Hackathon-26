"""Cross-cutting tables (schema.sql sections 23, 24, 25)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DepartmentScore(Base):
    __tablename__ = "department_scores"
    __table_args__ = (
        UniqueConstraint("department_id", "period", name="uq_department_scores"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"), nullable=False
    )
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    e_score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    s_score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    g_score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    total_score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(60), nullable=False, default="INFO")
    link: Mapped[str | None] = mapped_column(String(400))
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Settings(Base):
    __tablename__ = "settings"
    __table_args__ = (CheckConstraint("id = 1", name="chk_settings_singleton"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    gamification_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    csr_module_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    public_leaderboard: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    evidence_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_award_badges: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_emission_calc: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    esg_weights: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=lambda: {"E": 40, "S": 30, "G": 30}
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
