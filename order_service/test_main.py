"""
order_service/test_main.py
Pytest suite for Order Service.
Uses in-memory SQLite database, FastAPI TestClient, and unittest.mock to mock
external Inventory HTTP calls and AWS SQS publishing.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from jose import jwt

from sqlalchemy.pool import StaticPool

from order_service.main import app
from order_service.database import Base, get_db

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

# Secret key & algorithm matching order_service/auth.py & user_service/security.py
SECRET_KEY = "smartretailx_secret_key_2025"
ALGORITHM = "HS256"


def create_mock_jwt_token(user_id: int = 1, email: str = "customer@smartretailx.com", role: str = "customer") -> str:
    """Generates a valid signed JWT bearer token for testing."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ── Test Suite ────────────────────────────────────────────────────────────────

def test_health_check():
    """Asserts GET /health returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "order-service"


@patch("boto3.client")
@patch("requests.post")
def test_create_order_authorized_success(mock_requests_post, mock_boto3_client):
    """
    Asserts POST /orders creates an order when provided a valid Bearer JWT.
    Mocks HTTP calls to Inventory Service and AWS SQS client.
    """
    # 1. Mock synchronous HTTP call to Inventory Service (200 OK stock deduction)
    mock_http_response = MagicMock()
    mock_http_response.status_code = 200
    mock_http_response.text = '{"status": "success", "message": "Stock deducted"}'
    mock_requests_post.return_value = mock_http_response

    # 2. Mock boto3 SQS client to prevent real AWS calls
    mock_sqs = MagicMock()
    mock_sqs.send_message.return_value = {"MessageId": "mock-sqs-msg-12345"}
    mock_boto3_client.return_value = mock_sqs

    # 3. Generate mock JWT token & Authorization header
    token = create_mock_jwt_token(user_id=1, email="customer@smartretailx.com", role="customer")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "user_id": 1,
        "shipping_address": "456 Enterprise Way, London, UK",
        "items": [
            {
                "product_id": 1,
                "product_name": "ProBook 15-inch Business Laptop",
                "quantity": 2,
                "unit_price": 999.99,
            },
            {
                "product_id": 2,
                "product_name": "Ergo Wireless Mouse",
                "quantity": 1,
                "unit_price": 49.99,
            },
        ],
    }

    # 4. Execute request
    response = client.post("/orders", json=payload, headers=headers)
    assert response.status_code == 201

    data = response.json()
    assert data["id"] is not None
    assert data["user_id"] == 1
    assert data["status"] == "pending"
    assert data["total_amount"] == 2049.97
    assert len(data["items"]) == 2
    assert data["items"][0]["product_id"] == 1
    assert data["items"][0]["quantity"] == 2


def test_create_order_unauthorized():
    """
    Asserts POST /orders returns 401/403 Unauthorized when no Authorization header is provided.
    """
    payload = {
        "user_id": 1,
        "shipping_address": "789 Unauthenticated Ave",
        "items": [
            {
                "product_id": 1,
                "product_name": "ProBook 15-inch Business Laptop",
                "quantity": 1,
                "unit_price": 999.99,
            }
        ],
    }
    # No Authorization header provided
    response = client.post("/orders", json=payload)
    assert response.status_code in (401, 403)
