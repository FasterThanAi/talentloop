import pytest
from fastapi import HTTPException

from app.core.db import Base, SessionLocal, engine
from app.core.guards import assert_contactable, require_approved
from app.models import Candidate, Organization, OutreachMessage


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


def test_guards_enforce_invariants():
    db = SessionLocal()
    try:
        # Create test org and candidate
        org = Organization(name="Guard Test Org")
        db.add(org)
        db.flush()

        cand = Candidate(
            org_id=org.id,
            full_name="Opted Out Person",
            email="optedout@example.com",
            do_not_contact=True
        )
        db.add(cand)
        db.flush()

        # 1. Assert contactable fails with 403 on do_not_contact
        with pytest.raises(HTTPException) as exc_info:
            assert_contactable(db, cand.id)
        assert exc_info.value.status_code == 403

        # 2. Assert require_approved fails with 409 on draft status
        msg = OutreachMessage(
            org_id=org.id,
            pipeline_entry_id="test_pe_id",
            subject="Hello",
            body="World",
            status="draft"
        )
        db.add(msg)
        db.flush()

        with pytest.raises(HTTPException) as exc_msg_info:
            require_approved(db, msg.id)
        assert exc_msg_info.value.status_code == 409

    finally:
        db.rollback()
        db.close()
