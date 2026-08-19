import pytest
from fastapi.testclient import TestClient
from inventory_service.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "healthy"
    assert data.get("service") == "inventory-service"


def test_get_all_inventory():
    response = client.get("/inventory")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
