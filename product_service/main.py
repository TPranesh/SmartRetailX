"""
product_service/main.py
FastAPI application for the Product Catalogue Service.
Runs on: http://localhost:8002
Swagger UI: http://localhost:8002/docs

Phase 2: Startup seeds 4 realistic B2B products if catalogue is empty.
"""

import logging

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

from product_service.database import engine, get_db, Base, SessionLocal
from product_service.models import Product
from product_service.schemas import ProductCreate, ProductUpdate, ProductResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("product_service")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SmartRetailX — Product Catalogue Service",
    description=(
        "Full CRUD management for the SmartRetailX B2B product catalogue. "
        "Supports filtering by category. Seeded with 4 enterprise products on first run."
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

SEED_PRODUCTS = [
    {
        "name": "Enterprise SSD 2TB",
        "description": "High-speed NVMe SSD for data centre deployments. Rated for 24/7 enterprise workloads with a 5-year warranty.",
        "price": 299.99,
        "stock_level": 120,
        "category": "Storage",
        "sku": "SSD-2TB-ENT-001",
    },
    {
        "name": "Cloud Server Rack Unit",
        "description": "1U rack-mounted compute node with dual Xeon processors, 256GB RAM, and redundant power supplies.",
        "price": 4750.00,
        "stock_level": 45,
        "category": "Servers",
        "sku": "SRV-1U-XEON-002",
    },
    {
        "name": "10GbE Network Switch 48P",
        "description": "Managed 48-port 10 Gigabit Ethernet switch with 4x 40GbE uplinks. Ideal for top-of-rack deployments.",
        "price": 1899.50,
        "stock_level": 80,
        "category": "Networking",
        "sku": "NET-SW-10G-48P-003",
    },
    {
        "name": "UPS Power Module 10kVA",
        "description": "Online double-conversion UPS with 10kVA capacity, 8-minute runtime at full load, and hot-swap batteries.",
        "price": 3200.00,
        "stock_level": 30,
        "category": "Power",
        "sku": "UPS-10KVA-DC-004",
    },
]


def seed_products(db: Session) -> None:
    """Inserts default products on first startup if the catalogue is empty."""
    if db.query(Product).count() == 0:
        for rec in SEED_PRODUCTS:
            db.add(Product(**rec))
        db.commit()
        logger.info("Seeded %d products into the catalogue.", len(SEED_PRODUCTS))
    else:
        logger.info("Products table already populated — skipping seed.")


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup_tasks():
    db = SessionLocal()
    try:
        seed_products(db)
    finally:
        db.close()


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"], summary="Service health check")
def health_check():
    return {"status": "healthy", "service": "product-service", "port": 8002, "phase": 2}


# ── Product CRUD ──────────────────────────────────────────────────────────────

@app.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Products"],
    summary="Create a new product",
)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    """Adds a new product to the catalogue. SKU must be unique if provided."""
    if payload.sku:
        existing = db.query(Product).filter(Product.sku == payload.sku).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"SKU '{payload.sku}' already exists.")
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.get(
    "/products",
    response_model=List[ProductResponse],
    tags=["Products"],
    summary="List all products",
)
def list_products(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Returns a paginated list of products. Optionally filter by `category`."""
    query = db.query(Product)
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
    return query.offset(skip).limit(limit).all()


@app.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    tags=["Products"],
    summary="Get a product by ID",
)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found.")
    return product


@app.put(
    "/products/{product_id}",
    response_model=ProductResponse,
    tags=["Products"],
    summary="Update a product",
)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)):
    """Partially updates product fields. Only provided fields are changed."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@app.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Products"],
    summary="Delete a product",
)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found.")
    db.delete(product)
    db.commit()
