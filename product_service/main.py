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
        "name": "ProBook 15-inch Business Laptop",
        "description": "High-performance 15-inch business laptop with Intel Core i7, 16GB RAM, and 512GB SSD for workplace productivity.",
        "price": 1200.00,
        "stock_level": 50,
        "category": "Compute",
        "sku": "CMP-LPT-001",
    },
    {
        "name": "Ergo Wireless Mouse",
        "description": "Ergonomic wireless mouse with multi-device Bluetooth pairing and long-lasting rechargeable battery.",
        "price": 45.99,
        "stock_level": 50,
        "category": "Accessories",
        "sku": "ACC-MOU-001",
    },
    {
        "name": "Enterprise RTX 4000 Ada GPU",
        "description": "High-performance enterprise graphics card optimized for AI training, rendering, and complex compute workloads.",
        "price": 1850.00,
        "stock_level": 50,
        "category": "Compute",
        "sku": "CMP-GPU-001",
    },
    {
        "name": "Enterprise 4TB NVMe SSD",
        "description": "Ultra-fast enterprise 4TB NVMe SSD for heavy data storage, virtualization, and server workloads.",
        "price": 299.00,
        "stock_level": 50,
        "category": "Storage",
        "sku": "STG-SSD-001",
    },
    {
        "name": "24-Port Gigabit Network Switch",
        "description": "Reliable 24-port Gigabit Ethernet managed switch for office, enterprise, and data center networking.",
        "price": 350.00,
        "stock_level": 50,
        "category": "Networking",
        "sku": "NET-SW-001",
    },
    {
        "name": "Next-Gen Hardware Firewall",
        "description": "Advanced enterprise hardware firewall with deep packet inspection, VPN, and intrusion prevention.",
        "price": 1500.00,
        "stock_level": 50,
        "category": "Security",
        "sku": "SEC-FW-001",
    },
]


def seed_products(db: Session) -> None:
    """Inserts or updates default products for items 1..6."""
    for idx, rec in enumerate(SEED_PRODUCTS, start=1):
        p = db.query(Product).filter((Product.id == idx) | (Product.sku == rec["sku"])).first()
        if p:
            p.name = rec["name"]
            p.description = rec["description"]
            p.price = rec["price"]
            p.category = rec["category"]
            p.sku = rec["sku"]
        else:
            db.add(Product(id=idx, **rec))
    db.commit()
    logger.info("Seeded/updated %d core products in the catalogue.", len(SEED_PRODUCTS))


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
@app.get("/products/health", tags=["Health"], summary="Service health check (routed)")
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
@app.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@app.post("/products/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
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
@app.get("", response_model=List[ProductResponse], include_in_schema=False)
@app.get("/products/products", response_model=List[ProductResponse], include_in_schema=False)
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
@app.get("/{product_id}", response_model=ProductResponse, include_in_schema=False)
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
@app.put("/{product_id}", response_model=ProductResponse, include_in_schema=False)
@app.patch(
    "/products/{product_id}",
    response_model=ProductResponse,
    tags=["Products"],
    summary="Partially update a product",
)
@app.patch("/{product_id}", response_model=ProductResponse, include_in_schema=False)
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
@app.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found.")
    db.delete(product)
    db.commit()
