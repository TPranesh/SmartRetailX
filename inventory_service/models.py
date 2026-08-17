"""
inventory_service/models.py
SQLAlchemy ORM model for the Inventory table.
Each record mirrors a product but is owned solely by this service (no shared DB).
"""

from sqlalchemy import Column, Integer, String, DateTime, func
from inventory_service.database import Base


class InventoryItem(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, unique=True, index=True, nullable=False)
    product_name = Column(String(200), nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False)
    reserved_quantity = Column(Integer, default=0, nullable=False)  # Units held for pending orders
    warehouse_location = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
