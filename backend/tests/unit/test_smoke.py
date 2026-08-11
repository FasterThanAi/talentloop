import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_smoke_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "db" in data
    assert "pgvector" in data
    assert data["version"] == "0.1.0"
