"""
user_service/database.py
Handles SQLAlchemy engine creation and session management for the User Service.
Configured to use a local SQLite file: users.db

Phase 2 Note: Replace the DATABASE_URL with a PostgreSQL/RDS connection string
and remove check_same_thread=False (SQLite-only workaround).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///./users.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite-specific; remove for Postgres
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that provides a scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
