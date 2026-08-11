import uuid
import pytest
from fastapi.testclient import TestClient
from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models import Organization, User
from app.core.security import create_access_token, hash_password

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


def test_idempotency_key_deduplication():
    db = SessionLocal()
    org = Organization(name=f"Idempotency Org {uuid.uuid4().hex[:6]}")
    db.add(org)
    db.flush()

    user = User(
        org_id=org.id,
        email=f"recruiter_{uuid.uuid4().hex[:8]}@idem.dev",
        password_hash=hash_password("password123"),
        role="recruiter"
    )
    db.add(user)
    db.commit()

    token = create_access_token({"sub": user.id, "org_id": org.id, "role": "recruiter", "email": user.email})
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": f"key_{uuid.uuid4().hex}"
    }

    # 1. First POST request
    resp1 = client.post(
        "/api/v1/requisitions",
        json={"title": "Idempotent Role", "jd_raw": "Looking for Python engineer.", "seniority": "senior"},
        headers=headers
    )
    assert resp1.status_code == 201
    data1 = resp1.json()

    # 2. Duplicate POST request with same Idempotency-Key
    resp2 = client.post(
        "/api/v1/requisitions",
        json={"title": "Idempotent Role", "jd_raw": "Looking for Python engineer.", "seniority": "senior"},
        headers=headers
    )
    assert resp2.status_code == 201
    assert resp2.headers.get("x-cache-lookup") == "HIT-IDEMPOTENT"
    data2 = resp2.json()

    # Verify identical response body
    assert data1["id"] == data2["id"]
    assert data1["title"] == data2["title"]
