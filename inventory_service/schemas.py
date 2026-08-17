"""
inventory_service/schemas.py
Pydantic v2 schemas for request validation and response serialisation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── Request Schemas ───────────────────────────────────────────────────────────

class InventoryItemCreate(BaseModel):
    product_id: int = Field(..., examples=[1])
    product_name: str = Field(..., examples=["Enterprise SSD 2TB"])
    stock_quantity: int = Field(default=0, ge=0, examples=[100])
    warehouse_location: Optional[str] = Field(default=None, examples=["Warehouse A - Shelf 3"])


class StockDeductRequest(BaseModel):
    product_id: int = Field(..., examples=[1])
    quantity: int = Field(..., gt=0, examples=[5])


class OrderPlacedEvent(BaseModel):
    """
    Phase 2 Note: This schema is the contract for the AWS SQS message body.
    The handle_order_placed_event endpoint will be replaced with an SQS
    long-polling consumer (boto3 sqs.receive_message) that deserialises this
    exact payload from the SQS message body JSON.
    """
    order_id: int
    user_id: int
    items: List[dict]  # [{product_id, quantity, unit_price, product_name}]


# ── Response Schemas ──────────────────────────────────────────────────────────

class InventoryItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    stock_quantity: int
    reserved_quantity: int
    warehouse_location: Optional[str]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class StockDeductResponse(BaseModel):
    product_id: int
    deducted: int
    remaining_stock: int
    message: str
