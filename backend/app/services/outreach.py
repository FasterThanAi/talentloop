import logging
from datetime import UTC, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.runner import run_structured
from app.core.audit import write_audit
from app.core.deps import problem_detail_error
from app.core.guards import assert_contactable, require_approved
from app.models import Candidate, CandidateResearch, OutreachMessage, PipelineEntry, Requisition, User
from app.schemas.ai import IdealProfile, OutreachDraft
from app.services.gmail import send_gmail_message

logger = logging.getLogger("talentloop.outreach")


def utcnow() -> datetime:
    return datetime.now(UTC)


async def draft_outreach_message(
    db: Session,
    pipeline_entry_id: str,
    actor_id: str
) -> OutreachMessage:
    stmt = select(PipelineEntry).where(PipelineEntry.id == pipeline_entry_id)
    pe = db.execute(stmt).scalar_one_or_none()
    if not pe:
        raise problem_detail_error(
            status_code=404,
            title="Pipeline entry not found",
            detail=f"Entry {pipeline_entry_id} does not exist.",
            code="PIPELINE_ENTRY_NOT_FOUND"
        )

    # Re-check contactability before drafting
    assert_contactable(db, pe.candidate_id)

    stmt_req = select(Requisition).where(Requisition.id == pe.requisition_id)
    req = db.execute(stmt_req).scalar_one_or_none()

    stmt_cand = select(Candidate).where(Candidate.id == pe.candidate_id)
    cand = db.execute(stmt_cand).scalar_one_or_none()

    stmt_res = select(CandidateResearch).where(CandidateResearch.candidate_id == pe.candidate_id)
    res = db.execute(stmt_res).scalar_one_or_none()

    # Assemble top scoring dimensions for context
    top_dims = []
    if pe.score_breakdown and "dimensions" in pe.score_breakdown:
        top_dims = sorted(pe.score_breakdown["dimensions"], key=lambda x: x.get("score", 0), reverse=True)[:2]

    draft_result, _ = await run_structured(
        prompt_name="outreach.v1",
        variables={
            "ideal_profile": req.parsed_profile if req and req.parsed_profile else {"role_title": req.title if req else "Role"},
            "candidate_evidence": {
                "summary": res.summary if res else "Demonstrated software experience",
                "skills": res.skills if res else [],
                "projects": res.projects if res else []
            },
            "top_dimensions": top_dims
        },
        schema=OutreachDraft,
        temperature=0.7
    )

    # Check for existing draft or create new message
    stmt_msg = select(OutreachMessage).where(OutreachMessage.pipeline_entry_id == pe.id)
    msg = db.execute(stmt_msg).scalar_one_or_none()

    if not msg:
        msg = OutreachMessage(
            org_id=pe.org_id,
            pipeline_entry_id=pe.id,
            channel="email",
            subject=draft_result.subject,
            body=draft_result.body,
            status="draft"
        )
        db.add(msg)
        # The id column's default (generate_uuid) is applied by SQLAlchemy at INSERT time,
        # not when the Python object is constructed. Without this flush msg.id is still
        # None a few lines below, and write_audit() then violates the NOT NULL constraint
        # on audit_events.entity_id — taking the whole draft down with it.
        db.flush()
    else:
        msg.subject = draft_result.subject
        msg.body = draft_result.body
        msg.status = "draft"
        msg.approved_by = None
        msg.approved_at = None

    pe.stage = "outreach_drafted"

    write_audit(
        db=db,
        org_id=pe.org_id,
        actor_id=actor_id,
        action="outreach_drafted",
        entity="outreach_message",
        entity_id=msg.id,
        payload={"subject": msg.subject, "reference_used": draft_result.specific_reference_used}
    )

    db.commit()
    db.refresh(msg)
    return msg


def approve_outreach_message(
    db: Session,
    message_id: str,
    user: User
) -> OutreachMessage:
    stmt = select(OutreachMessage).where(OutreachMessage.id == message_id)
    msg = db.execute(stmt).scalar_one_or_none()
    if not msg:
        raise problem_detail_error(
            status_code=404,
            title="Outreach message not found",
            detail=f"Message {message_id} does not exist.",
            code="OUTREACH_NOT_FOUND"
        )

    msg.status = "approved"
    msg.approved_by = user.id
    msg.approved_at = utcnow()

    write_audit(
        db=db,
        org_id=msg.org_id,
        actor_id=user.id,
        action="outreach_approved",
        entity="outreach_message",
        entity_id=msg.id,
        payload={"approved_by": user.email, "timestamp": msg.approved_at.isoformat()}
    )

    db.commit()
    db.refresh(msg)
    return msg


def send_outreach_message(
    db: Session,
    message_id: str,
    user: User
) -> OutreachMessage:
    # 1. Guard check: Must be in 'approved' state (returns 409 if not approved)
    msg = require_approved(db, message_id)

    # 2. Guard check: Re-verify candidate contactability immediately before dispatch (returns 403)
    stmt_pe = select(PipelineEntry).where(PipelineEntry.id == msg.pipeline_entry_id)
    pe = db.execute(stmt_pe).scalar_one_or_none()
    if not pe:
        raise problem_detail_error(status_code=404, title="Entry not found", detail="Pipeline entry not found", code="PIPELINE_ENTRY_NOT_FOUND")

    candidate = assert_contactable(db, pe.candidate_id)

    # 3. Dispatch email via Gmail
    send_result = send_gmail_message(
        user=user,
        to_email=candidate.email,
        subject=msg.subject,
        body=msg.body
    )

    msg.status = "sent"
    msg.sent_at = utcnow()
    msg.gmail_message_id = send_result.get("id")
    pe.stage = "contacted"

    write_audit(
        db=db,
        org_id=msg.org_id,
        actor_id=user.id,
        action="outreach_sent",
        entity="outreach_message",
        entity_id=msg.id,
        payload={"recipient": candidate.email, "gmail_id": msg.gmail_message_id}
    )

    db.commit()
    db.refresh(msg)
    return msg


def bulk_send_approved_messages(
    db: Session,
    requisition_id: str,
    user: User
) -> dict[str, Any]:
    stmt = (
        select(OutreachMessage)
        .join(PipelineEntry, OutreachMessage.pipeline_entry_id == PipelineEntry.id)
        .where(
            PipelineEntry.requisition_id == requisition_id,
            OutreachMessage.status == "approved"
        )
    )
    approved_messages = db.execute(stmt).scalars().all()

    sent_count = 0
    failed_count = 0
    results = []

    for msg in approved_messages:
        try:
            send_outreach_message(db=db, message_id=msg.id, user=user)
            sent_count += 1
            results.append({"message_id": msg.id, "status": "sent"})
        except Exception as e:
            failed_count += 1
            results.append({"message_id": msg.id, "status": "failed", "error": str(e)})

    return {
        "sent_count": sent_count,
        "failed_count": failed_count,
        "results": results
    }
