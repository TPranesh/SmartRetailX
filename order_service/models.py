"""
order_service/models.py
SQLAlchemy ORM models for the Orders and OrderItems tables.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from order_service.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    status = Column(String(50), default="pending")  # pending | confirmed | shipped | delivered | cancelled
    total_amount = Column(Float, nullable=False)
    shipping_address = Column(String(500), nullable=True)
    # Phase 2 Note: On status change to "confirmed", publish an OrderPlaced event
    # to an AWS SNS topic. The Inventory Service SQS queue subscribes to this topic.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, nullable=False)
    product_name = Column(String(200), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
