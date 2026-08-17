"""
order_service/schemas.py
Pydantic v2 schemas for request validation and response serialisation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── Sub-schemas ───────────────────────────────────────────────────────────────

class OrderItemCreate(BaseModel):
    product_id: int = Field(..., examples=[1])
    product_name: str = Field(..., examples=["Enterprise SSD 2TB"])
    quantity: int = Field(..., gt=0, examples=[2])
    unit_price: float = Field(..., gt=0, examples=[299.99])


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price: float

    model_config = {"from_attributes": True}


# ── Request Schemas ───────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    user_id: int = Field(..., examples=[1])
    items: List[OrderItemCreate] = Field(..., min_length=1)
    shipping_address: Optional[str] = Field(default=None, examples=["123 Main St, London, UK"])


class OrderStatusUpdate(BaseModel):
    """
    Phase 2 Note: When status changes to 'confirmed', this endpoint will also
    publish an 'OrderPlaced' event to AWS SNS/EventBridge so the Inventory
    Service can consume it via its SQS queue (Saga Pattern).
    """
    status: str = Field(..., examples=["confirmed", "shipped", "delivered", "cancelled"])


# ── Response Schemas ──────────────────────────────────────────────────────────

class OrderResponse(BaseModel):
    id: int
    user_id: int
    status: str
    total_amount: float
    shipping_address: Optional[str]
    items: List[OrderItemResponse]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}
