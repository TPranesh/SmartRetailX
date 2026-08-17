"""
product_service/models.py
SQLAlchemy ORM model for the Products table.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, func
from product_service.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)
    price = Column(Float, nullable=False)
    stock_level = Column(Integer, default=0, nullable=False)
    category = Column(String(100), nullable=True)
    sku = Column(String(100), unique=True, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
