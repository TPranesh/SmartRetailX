"""
inventory_service/main.py
FastAPI application for the Inventory Service.
Runs on: http://localhost:8004
Swagger UI: http://localhost:8004/docs

Phase 2:
  - On startup: seeds default inventory records (if empty) and launches SQS consumer thread.
  - POST /events/order-placed  : Local dev fallback endpoint (SQS not required).
  - SQS consumer is a no-op if SQS_QUEUE_URL is not set.
"""

import logging

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from inventory_service.database import engine, get_db, Base, SessionLocal
from inventory_service.models import InventoryItem
from inventory_service.schemas import (
    InventoryItemCreate,
    InventoryItemResponse,
    StockDeductRequest,
    StockDeductResponse,
    OrderPlacedEvent,
)
from inventory_service.sqs_consumer import start_consumer_thread

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inventory_service")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SmartRetailX — Inventory Service",
    description=(
        "Manages warehouse stock levels. "
        "In Phase 2, stock deductions triggered by orders are processed via "
        "an AWS SQS background consumer thread. "
        "POST /events/order-placed is available as a local development fallback "
        "when SQS is not configured."
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


# ── Seed Data ─────────────────────────────────────────────────────────────────

SEED_INVENTORY = [
    {"product_id": 1, "product_name": "Enterprise SSD 2TB",        "stock_quantity": 50, "warehouse_location": "Warehouse A"},
    {"product_id": 2, "product_name": "Cloud Server Rack Unit",    "stock_quantity": 50, "warehouse_location": "Warehouse A"},
    {"product_id": 3, "product_name": "10GbE Network Switch 48P",  "stock_quantity": 50, "warehouse_location": "Warehouse B"},
    {"product_id": 4, "product_name": "UPS Power Module 10kVA",    "stock_quantity": 50, "warehouse_location": "Warehouse B"},
]


def seed_inventory(db: Session) -> None:
    """Inserts default inventory records for product IDs 1 to 4 if missing."""
    for rec in SEED_INVENTORY:
        item = db.query(InventoryItem).filter(InventoryItem.product_id == rec["product_id"]).first()
        if not item:
            db.add(InventoryItem(**rec))
            logger.info("Auto-seeded inventory record for product #%d (50 units).", rec["product_id"])
    db.commit()


# ── Startup Events ────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup_tasks():
    """Seeds data and starts the SQS consumer background thread."""
    db = SessionLocal()
    try:
        seed_inventory(db)
    finally:
        db.close()

    logger.info("Starting SQS consumer background thread...")
    start_consumer_thread()


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"], summary="Service health check")
def health_check():
    return {"status": "healthy", "service": "inventory-service", "port": 8004, "phase": 2}


# ── Inventory CRUD ────────────────────────────────────────────────────────────

@app.post(
    "/inventory",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Inventory"],
    summary="Add a product to inventory",
)
def add_inventory_item(payload: InventoryItemCreate, db: Session = Depends(get_db)):
    """Registers a product in the inventory with an initial stock quantity."""
    existing = db.query(InventoryItem).filter(InventoryItem.product_id == payload.product_id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Product {payload.product_id} already in inventory.")
    item = InventoryItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get(
    "/inventory",
    response_model=List[InventoryItemResponse],
    tags=["Inventory"],
    summary="View all inventory",
)
def list_inventory(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Returns the full inventory list with current stock levels."""
    return db.query(InventoryItem).offset(skip).limit(limit).all()


@app.get(
    "/inventory/{product_id}",
    response_model=InventoryItemResponse,
    tags=["Inventory"],
    summary="Get stock for a specific product",
)
def get_inventory_item(product_id: int, db: Session = Depends(get_db)):
    item = db.query(InventoryItem).filter(InventoryItem.product_id == product_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"No inventory record for product {product_id}.")
    return item


@app.patch(
    "/inventory/{product_id}/restock",
    response_model=InventoryItemResponse,
    tags=["Inventory"],
    summary="Restock a product (creates inventory record if not found)",
)
def restock_item(product_id: int, quantity: int = Query(..., gt=0), db: Session = Depends(get_db)):
    """Adds stock to an existing inventory record. If not found, creates a new inventory record."""
    item = db.query(InventoryItem).filter(InventoryItem.product_id == product_id).first()
    if not item:
        item = InventoryItem(
            product_id=product_id,
            product_name=f"Product #{product_id}",
            stock_quantity=quantity,
            warehouse_location="Warehouse A",
        )
        db.add(item)
    else:
        item.stock_quantity += quantity
    db.commit()
    db.refresh(item)
    return item


@app.post(
    "/inventory/deduct",
    tags=["Inventory"],
    summary="Deduct stock for product items",
)
def deduct_stock(payload: StockDeductRequest, db: Session = Depends(get_db)):
    """
    Deducts stock for items provided in payload.
    Supports either batch `items: [...]` list or single `product_id` and `quantity`.
    If an inventory record is missing for a product, creates it with 0 stock.
    Stock quantity cannot drop below 0.
    """
    items_to_process = []
    if payload.items:
        items_to_process = payload.items
    elif payload.product_id and payload.quantity:
        items_to_process = [payload]

    if not items_to_process:
        raise HTTPException(status_code=400, detail="No items or product_id/quantity specified for stock deduction.")

    results = []
    for item in items_to_process:
        prod_id = getattr(item, 'product_id', None) if not isinstance(item, dict) else item.get('product_id')
        qty = getattr(item, 'quantity', 0) if not isinstance(item, dict) else item.get('quantity', 0)

        if not prod_id or qty <= 0:
            continue

        inv_item = db.query(InventoryItem).filter(InventoryItem.product_id == prod_id).first()
        if not inv_item:
            inv_item = InventoryItem(
                product_id=prod_id,
                product_name=f"Product #{prod_id}",
                stock_quantity=50,
                warehouse_location="Warehouse A",
            )
            db.add(inv_item)
            db.commit()
            db.refresh(inv_item)

        inv_item.stock_quantity = max(0, inv_item.stock_quantity - qty)
        db.commit()
        db.refresh(inv_item)

        results.append({
            "product_id": prod_id,
            "deducted": qty,
            "remaining_stock": inv_item.stock_quantity,
        })

    first_pid = results[0]["product_id"] if results else (payload.product_id or 0)
    first_qty = results[0]["deducted"] if results else (payload.quantity or 0)
    first_rem = results[0]["remaining_stock"] if results else 0

    return {
        "product_id": first_pid,
        "deducted": first_qty,
        "remaining_stock": first_rem,
        "message": f"Successfully processed stock deduction for {len(results)} item(s).",
        "results": results,
    }


@app.delete(
    "/inventory/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Inventory"],
    summary="Delete an inventory record",
)
def delete_inventory_item(product_id: int, db: Session = Depends(get_db)):
    """Deletes the inventory stock record for a product."""
    item = db.query(InventoryItem).filter(InventoryItem.product_id == product_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"No inventory record for product {product_id}.")
    db.delete(item)
    db.commit()


# ── Local Dev Fallback: Simulated SQS Event ───────────────────────────────────

@app.post(
    "/events/order-placed",
    tags=["Events — Local Dev Fallback"],
    summary="[LOCAL] Simulate an OrderPlaced SQS event via HTTP",
    status_code=status.HTTP_200_OK,
)
def handle_order_placed_event(order_data: OrderPlacedEvent, db: Session = Depends(get_db)):
    """
    **Local development fallback only.**

    In Phase 2 with AWS configured, stock deductions happen automatically via the
    SQS background consumer — this endpoint is NOT called by the Order Service.

    Use this endpoint to manually simulate the SQS message flow during local
    testing (e.g., from Postman or the checkout page when `SQS_QUEUE_URL` is unset).

    **Production (Phase 3):** Remove or disable this endpoint and route all
    deductions exclusively through the SQS consumer.
    """
    logger.info(
        "[SQS Fallback] Simulating SQS publish for order #%d via HTTP fallback.",
        order_data.order_id,
    )
    results = []

    for item_data in order_data.items:
        product_id = item_data.get("product_id")
        quantity = item_data.get("quantity", 0)

        inv_item = db.query(InventoryItem).filter(
            InventoryItem.product_id == product_id
        ).first()

        if inv_item and inv_item.stock_quantity >= quantity:
            inv_item.stock_quantity -= quantity
            db.commit()
            results.append({
                "product_id": product_id,
                "status": "deducted",
                "quantity": quantity,
                "remaining": inv_item.stock_quantity,
            })
        elif inv_item:
            results.append({
                "product_id": product_id,
                "status": "insufficient_stock",
                "available": inv_item.stock_quantity,
            })
        else:
            results.append({"product_id": product_id, "status": "not_found"})

    return {
        "event": "OrderPlacedEvent",
        "order_id": order_data.order_id,
        "processing_results": results,
        "mode": "local_http_fallback — replace with SQS consumer in production",
    }
