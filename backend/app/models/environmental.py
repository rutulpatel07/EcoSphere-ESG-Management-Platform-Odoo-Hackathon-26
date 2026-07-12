"""Environmental domain tables (schema.sql sections 3, 4, 5, 10, 11)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Date,
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
from app.models.enums import DataTier, OpType, pg_enum


class EmissionFactor(Base):
    __tablename__ = "emission_factors"
    __table_args__ = (
        UniqueConstraint("activity_type", "version", name="uq_emission_factors_activity_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_type: Mapped[str] = mapped_column(String(120), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    factor_value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    source: Mapped[str | None] = mapped_column(String(200))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
    uncertainty_pct: Mapped[float | None] = mapped_column(Numeric(6, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ProductESGProfile(Base):
    __tablename__ = "product_esg_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str | None] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    embodied_carbon_kg: Mapped[float | None] = mapped_column(Numeric(18, 6))
    recyclable_pct: Mapped[float | None] = mapped_column(Numeric(6, 2))
    water_usage_l: Mapped[float | None] = mapped_column(Numeric(18, 6))
    ethical_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    certifications: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EnvironmentalGoal(Base):
    __tablename__ = "environmental_goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    metric: Mapped[str] = mapped_column(String(120), nullable=False)
    baseline_value: Mapped[float | None] = mapped_column(Numeric(18, 6))
    target_value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    current_value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    unit: Mapped[str | None] = mapped_column(String(40))
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL")
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="ON_TRACK")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OperationalRecord(Base):
    __tablename__ = "operational_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    op_type: Mapped[OpType] = mapped_column(pg_enum(OpType, "op_type"), nullable=False)
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL")
    )
    activity_type: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(200))
    amount: Mapped[float | None] = mapped_column(Numeric(18, 2))
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CarbonTransaction(Base):
    __tablename__ = "carbon_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    operational_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("operational_records.id", ondelete="CASCADE")
    )
    emission_factor_id: Mapped[int | None] = mapped_column(
        ForeignKey("emission_factors.id", ondelete="SET NULL")
    )
    factor_value_used: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    factor_version_used: Mapped[int | None] = mapped_column()
    quantity: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    co2e_kg: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    scope: Mapped[int | None] = mapped_column(SmallInteger)
    data_tier: Mapped[DataTier] = mapped_column(
        pg_enum(DataTier, "data_tier"), nullable=False, default=DataTier.ESTIMATED
    )
    uncertainty_pct: Mapped[float | None] = mapped_column(Numeric(6, 2))
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL")
    )
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
