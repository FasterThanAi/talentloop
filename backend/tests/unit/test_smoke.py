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


def test_health_reports_operational_mode():
    """
    These three fields are what stop us demoing on mock AI or SQLite by accident, so the
    contract is pinned: /health must always say which database, which vector backend and
    which model are actually live.
    """
    data = client.get("/api/v1/health").json()
    assert data["db_dialect"] in ("postgresql", "sqlite")
    assert data["vector_backend"] in ("pgvector", "json-cosine")
    assert data["ai_mode"]           # either "MOCK" or the configured model name
