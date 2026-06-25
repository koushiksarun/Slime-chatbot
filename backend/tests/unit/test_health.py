from fastapi.testclient import TestClient
import pytest
from app.main import app

client = TestClient(app)

def test_health_check():
    """Verify that the health check endpoint returns 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data

def test_root_endpoint():
    """Verify that the root endpoint redirects or returns info about the API."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "API" in data["message"]
    assert data["docs"] == "/docs"
