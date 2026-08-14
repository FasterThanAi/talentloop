"""
Invariant #2 applied to reply responses.

A drafted response to a candidate is a message that reaches a human, so it passes the same
gate as outreach: draft -> approve -> send, with send refusing anything not explicitly
approved and re-checking do-not-contact immediately before dispatch.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app.core.guards import require_response_approved
from app.models import (
    Candidate,
    Organization,
    OutreachMessage,
    PipelineEntry,
    Reply,
    Requisition,
    User,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _fixture_reply(db, *, response_status="draft", has_draft=True, do_not_contact=False):
    org = Organization(name="Acme")
    db.add(org)
    db.flush()

    user = User(org_id=org.id, email="r@acme.dev", password_hash="x", role="recruiter")
    cand = Candidate(
        org_id=org.id, full_name="Test Person", email="c@example.dev",
        source="csv", do_not_contact=do_not_contact,
    )
    db.add_all([user, cand])
    db.flush()   # need user.id before the requisition, which requires created_by

    req = Requisition(
        org_id=org.id,
        created_by=user.id,
        title="Backend Engineer",
        jd_raw="...",
        status="open",
    )
    db.add(req)
    db.flush()

    pe = PipelineEntry(org_id=org.id, requisition_id=req.id, candidate_id=cand.id, stage="contacted")
    db.add(pe)
    db.flush()

    msg = OutreachMessage(
        org_id=org.id, pipeline_entry_id=pe.id, channel="email",
        subject="Hi", body="Hello", status="sent",
    )
    db.add(msg)
    db.flush()

    reply = Reply(
        org_id=org.id,
        outreach_message_id=msg.id,
        raw_body="What is the salary range?",
        intent="salary_question",
        sentiment="neutral",
        priority="high",
        summary="Asked about compensation",
        suggested_action="Share the band",
        response_draft={"body": "Our band is..."} if has_draft else None,
        response_status=response_status,
    )
    db.add(reply)
    db.commit()
    return reply


def test_send_rejected_when_response_is_only_a_draft(db):
    reply = _fixture_reply(db, response_status="draft")
    with pytest.raises(Exception) as exc:
        require_response_approved(db, reply.id)
    assert getattr(exc.value, "status_code", None) == 409


def test_send_rejected_when_no_draft_exists(db):
    reply = _fixture_reply(db, response_status="none", has_draft=False)
    with pytest.raises(Exception) as exc:
        require_response_approved(db, reply.id)
    assert getattr(exc.value, "status_code", None) == 409


def test_send_allowed_only_after_explicit_approval(db):
    reply = _fixture_reply(db, response_status="approved")
    approved = require_response_approved(db, reply.id)
    assert approved.id == reply.id
    assert approved.response_status == "approved"


def test_unknown_reply_is_404(db):
    with pytest.raises(Exception) as exc:
        require_response_approved(db, "does-not-exist")
    assert getattr(exc.value, "status_code", None) == 404


def test_default_response_status_is_none(db):
    """A freshly classified reply must not start life in an approved state."""
    reply = _fixture_reply(db, response_status="none", has_draft=False)
    assert reply.response_status == "none"
    assert reply.response_approved_by is None
    assert reply.response_sent_at is None
