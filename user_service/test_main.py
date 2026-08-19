"""
user_service/test_main.py
Pytest suite for User Service.
Uses in-memory SQLite database and FastAPI TestClient.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.pool import StaticPool

from user_service.main import app
from user_service.database import Base, get_db

# ── In-Memory SQLite Setup for Isolated Testing ─────────────────────────────
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override FastAPI database dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


# ── Test Suite ────────────────────────────────────────────────────────────────

def test_health_check():
    """Asserts GET /health returns 200 OK and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "user-service"


def test_register_user_success():
    """
    Asserts POST /users/register creates a user account (200/201 status code)
    and ensures plain text password and hashed_password are NOT exposed in response JSON.
    """
    payload = {
        "full_name": "QA Test Customer",
        "email": "qa.customer@smartretailx.com",
        "password": "SuperSecretPass123!",
        "role": "customer",
        "company": "SmartRetailX QA",
    }
    response = client.post("/users/register", json=payload)
    assert response.status_code in (200, 201)

    data = response.json()
    assert data["email"] == "qa.customer@smartretailx.com"
    assert data["full_name"] == "QA Test Customer"
    assert data["role"] == "customer"
    
    # Security requirement: Plaintext and hashed passwords must NOT be returned in JSON payload
    assert "password" not in data
    assert "hashed_password" not in data


def test_login_user_success():
    """
    Asserts POST /users/login returns a valid JWT access_token given valid credentials.
    """
    # 1. Register candidate user
    register_payload = {
        "full_name": "QA Login User",
        "email": "qa.login@smartretailx.com",
        "password": "LoginSecret123!",
        "role": "customer",
        "company": "QA Corp",
    }
    reg_response = client.post("/users/register", json=register_payload)
    assert reg_response.status_code in (200, 201)

    # 2. Attempt login
    login_payload = {
        "email": "qa.login@smartretailx.com",
        "password": "LoginSecret123!",
    }
    login_response = client.post("/users/login", json=login_payload)
    assert login_response.status_code == 200

    data = login_response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["email"] == "qa.login@smartretailx.com"
    assert data["role"] == "customer"
