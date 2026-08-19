import pytest
from fastapi.testclient import TestClient
from product_service.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "healthy"
    assert data.get("service") == "product-service"


def test_get_all_products():
    response = client.get("/products")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_single_product():
    response = client.get("/products/1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "id" in data
    assert "name" in data
    assert "price" in data
    assert data["id"] == 1


def test_get_nonexistent_product():
    response = client.get("/products/9999")
    assert response.status_code == 404
