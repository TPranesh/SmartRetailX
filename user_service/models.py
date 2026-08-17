"""
user_service/models.py
SQLAlchemy ORM model for the Users table.
Phase 2: passwords stored as bcrypt hashes via passlib.
"""

from sqlalchemy import Column, Integer, String, DateTime, func
from user_service.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    # Phase 2: now stores a bcrypt hash, never the plain-text password
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="customer")  # 'customer' | 'admin' — encoded into JWT
    company = Column(String(150), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
