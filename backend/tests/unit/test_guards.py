"""
The two approval/consent guards, tested against a REAL row graph.

This test previously attached the outreach message to `pipeline_entry_id="test_pe_id"`, a
value that does not exist in pipeline_entries. SQLite does not enforce foreign keys by
default, so it passed locally and in CI — and failed the moment it was run against the
Postgres database the product actually uses. A test that only passes on the weaker engine
is not testing the thing it claims to. It now builds org → user → requisition → candidate →
pipeline entry properly, so it behaves identically on both.
"""
import uuid

import pytest
from fastapi import HTTPException

from app.core.db import Base, SessionLocal, engine
from app.core.guards import assert_contactable, require_approved
from app.models import (
    Candidate,
    Organization,
    OutreachMessage,
    PipelineEntry,
    Requisition,
    User,
)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


def test_guards_enforce_invariants():
    db = SessionLocal()
    try:
        org = Organization(name="Guard Test Org")
        db.add(org)
        db.flush()

        user = User(
            org_id=org.id,
            # Unique per run so repeated local runs against a real database do not collide.
            email=f"guard-test-{uuid.uuid4().hex[:8]}@example.com",
            password_hash="not-a-real-hash",
            role="recruiter",
        )
        db.add(user)
        db.flush()

        cand = Candidate(
            org_id=org.id,
            full_name="Opted Out Person",
            email=f"optedout-{uuid.uuid4().hex[:8]}@example.com",
            do_not_contact=True,
        )
        db.add(cand)
        db.flush()

        # Invariant 2a — a do-not-contact candidate can never be contacted.
        with pytest.raises(HTTPException) as exc_info:
            assert_contactable(db, cand.id)
        assert exc_info.value.status_code == 403

        req = Requisition(
            org_id=org.id,
            created_by=user.id,
            title="Guard Test Role",
            jd_raw="Raw job description used only by this test.",
        )
        db.add(req)
        db.flush()

        entry = PipelineEntry(org_id=org.id, requisition_id=req.id, candidate_id=cand.id)
        db.add(entry)
        db.flush()

        msg = OutreachMessage(
            org_id=org.id,
            pipeline_entry_id=entry.id,
            subject="Hello",
            body="World",
            status="draft",
        )
        db.add(msg)
        db.flush()

        # Invariant 2b — a draft is not sendable. Approval is a separate, explicit act.
        with pytest.raises(HTTPException) as exc_msg_info:
            require_approved(db, msg.id)
        assert exc_msg_info.value.status_code == 409

    finally:
        # Rollback, never commit: this test must leave no trace in a real database.
        db.rollback()
        db.close()
