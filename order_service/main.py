"""
order_service/main.py
FastAPI application for the Order Processing Service.
Runs on: http://localhost:8003
Swagger UI: http://localhost:8003/docs

Phase 2 changes:
  - POST /orders is now JWT-protected via Depends(get_current_user)
  - After committing an order, publishes an OrderPlacedEvent to AWS SQS
  - No direct HTTP call to Inventory Service — fully decoupled
"""

import logging

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

from order_service.database import engine, get_db, Base
from order_service.models import Order, OrderItem
from order_service.schemas import OrderCreate, OrderStatusUpdate, OrderResponse
from order_service.auth import get_current_user, TokenData
from order_service.sqs_publisher import publish_order_placed_event, publish_order_cancelled_event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order_service")

Base.metadata.create_all(bind=engine)

VALID_STATUSES = {"pending", "confirmed", "shipped", "delivered", "cancelled"}

app = FastAPI(
    title="SmartRetailX — Order Processing Service",
    description=(
        "Handles the lifecycle of customer orders. "
        "POST /orders requires a valid JWT Bearer token. "
        "On order creation, an OrderPlacedEvent is published to AWS SQS — "
        "the Inventory Service consumes it asynchronously."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"], summary="Service health check")
def health_check():
    return {"status": "healthy", "service": "order-service", "port": 8003, "phase": 2}


# ── Order Endpoints ───────────────────────────────────────────────────────────

@app.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Orders"],
    summary="Create a new order (JWT required)",
)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),  # 🔒 JWT guard
):
    """
    Places a new order for the authenticated user.

    **Requires:** `Authorization: Bearer <JWT>` header.

    **Event-Driven Flow (Phase 2):**
    1. Order is persisted to the orders.db SQLite database.
    2. An `OrderPlacedEvent` JSON message is published to the AWS SQS queue
       (`SQS_QUEUE_URL` env var). The Inventory Service's background thread
       picks this up and deducts stock asynchronously.
    3. If SQS is not configured, a warning is logged but the order still succeeds.
    """
    total = sum(item.quantity * item.unit_price for item in payload.items)
    order = Order(
        user_id=current_user.user_id,       # Use the verified ID from the JWT, not payload
        total_amount=round(total, 2),
        shipping_address=payload.shipping_address,
        status="pending",
    )
    db.add(order)
    db.flush()  # Get order.id before commit

    for item_data in payload.items:
        item = OrderItem(order_id=order.id, **item_data.model_dump())
        db.add(item)

    db.commit()
    db.refresh(order)
    logger.info("Order #%d created for user #%d (£%.2f)", order.id, order.user_id, order.total_amount)

    # ── Publish to SQS (decoupled from Inventory Service) ────────────────────
    items_payload = [
        {
            "product_id": i.product_id,
            "product_name": i.product_name,
            "quantity": i.quantity,
            "unit_price": i.unit_price,
        }
        for i in order.items
    ]
    published = publish_order_placed_event(
        order_id=order.id,
        user_id=order.user_id,
        items=items_payload,
    )
    if not published:
        logger.warning(
            "SQS publish skipped for order #%d — inventory deduction will not happen automatically.",
            order.id,
        )

    return order


@app.get(
    "/orders",
    response_model=List[OrderResponse],
    tags=["Orders"],
    summary="List all orders",
)
def list_orders(
    user_id: Optional[int] = Query(default=None, description="Filter by user ID"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Returns all orders. Supports filtering by user_id and status."""
    query = db.query(Order)
    if user_id:
        query = query.filter(Order.user_id == user_id)
    if status_filter:
        query = query.filter(Order.status == status_filter)
    return query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()


@app.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    tags=["Orders"],
    summary="Get an order by ID",
)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found.")
    return order


@app.patch(
    "/orders/{order_id}/status",
    response_model=OrderResponse,
    tags=["Orders"],
    summary="Update order status",
)
def update_order_status(order_id: int, payload: OrderStatusUpdate, db: Session = Depends(get_db)):
    """Transitions an order to a new status (admin action)."""
    if payload.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}",
        )
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found.")

    previous_status = order.status
    order.status = payload.status
    db.commit()
    db.refresh(order)

    # Trigger compensating transaction if status is changed to cancelled
    if payload.status == "cancelled" and previous_status != "cancelled":
        items_payload = [
            {
                "product_id": item.product_id,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
            }
            for item in order.items
        ]
        publish_order_cancelled_event(order.id, items_payload)

    return order


@app.get(
    "/orders/user/{user_id}",
    response_model=List[OrderResponse],
    tags=["Orders"],
    summary="Get order history for a user",
)
def get_user_order_history(user_id: int, db: Session = Depends(get_db)):
    """Returns the complete order history for a specific user, newest first."""
    return db.query(Order).filter(Order.user_id == user_id).order_by(Order.created_at.desc()).all()
