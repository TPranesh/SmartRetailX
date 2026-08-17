"""
product_service/schemas.py
Pydantic v2 schemas for request validation and response serialisation.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Request Schemas ──────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, examples=["Enterprise SSD 2TB"])
    description: Optional[str] = Field(default=None, max_length=1000, examples=["High-speed NVMe SSD for data centres"])
    price: float = Field(..., gt=0, examples=[299.99])
    stock_level: int = Field(default=0, ge=0, examples=[150])
    category: Optional[str] = Field(default=None, max_length=100, examples=["Storage"])
    sku: Optional[str] = Field(default=None, max_length=100, examples=["SSD-2TB-ENT-001"])


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    price: Optional[float] = Field(default=None, gt=0)
    stock_level: Optional[int] = Field(default=None, ge=0)
    category: Optional[str] = Field(default=None, max_length=100)


# ── Response Schemas ─────────────────────────────────────────────────────────

class ProductResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    stock_level: int
    category: Optional[str]
    sku: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}
