"""Request/response shapes for /environmental/products (CONTRACT.md)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ProductCreate(BaseModel):
    sku: str | None = None
    name: str
    embodied_carbon_kg: float | None = None
    recyclable_pct: float | None = None
    water_usage_l: float | None = None
    ethical_score: float | None = None
    certifications: list[str] = []


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str | None
    name: str
    embodied_carbon_kg: float | None
    recyclable_pct: float | None
    water_usage_l: float | None
    ethical_score: float | None
    certifications: list[str]
