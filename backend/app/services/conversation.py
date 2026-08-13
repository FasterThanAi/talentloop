import logging
from datetime import UTC, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.runner import run_structured
from app.core.audit import write_audit
from app.core.config import settings
from app.core.deps import problem_detail_error
from app.core.guards import assert_contactable, require_response_approved
from app.models import Candidate, OutreachMessage, PipelineEntry, Reply, User
from app.schemas.ai import ReplyClassification, ResponseDraft
from app.services.gmail import send_gmail_message
from app.services.knowledge import search_knowledge

logger = logging.getLogger("talentloop.conversation")


def utcnow() -> datetime:
    return datetime.now(UTC)


async def process_incoming_reply(
    db: Session,
    outreach_message_id: str,
    raw_body: str,
    actor_id: str = "system"
) -> Reply:
    stmt_msg = select(OutreachMessage).where(OutreachMessage.id == outreach_message_id)
    msg = db.execute(stmt_msg).scalar_one_or_none()
    if not msg:
        raise ValueError(f"OutreachMessage {outreach_message_id} not found")

    # 1. Classify reply using reply.v1 (temperature 0.0, closed enums)
    classification, _ = await run_structured(
        prompt_name="reply.v1",
        variables={
            "outreach_body": msg.body,
            "reply_body": raw_body
        },
        schema=ReplyClassification,
        temperature=0.0
    )

    # 2. Retrieval gate: retrieve knowledge facts for grounded response
    knowledge_results = search_knowledge(
        db=db,
        org_id=msg.org_id,
        query=raw_body,
        min_relevance=settings.RESPONSE_MIN_RELEVANCE
    )

    retrieved_facts_text = ""
    used_chunks = []
    if knowledge_results:
        retrieved_facts_text = "\n".join(f"[{c[0].id}] {c[0].content}" for c in knowledge_results)
        used_chunks = [c[0].id for c in knowledge_results]

    # 3. Draft response using respond.v1 (temp 0.3)
    response_draft, _ = await run_structured(
        prompt_name="respond.v1",
        variables={
            "reply_body": raw_body,
            "classification": classification.model_dump(),
            "knowledge_chunks": retrieved_facts_text
        },
        schema=ResponseDraft,
        temperature=0.3
    )

    reply = Reply(
        org_id=msg.org_id,
        outreach_message_id=msg.id,
        raw_body=raw_body,
        intent=classification.intent,
        sentiment=classification.sentiment,
        priority=classification.priority,
        summary=classification.summary,
        suggested_action=classification.suggested_action,
        response_draft=response_draft.model_dump(),
        received_at=utcnow()
    )
    db.add(reply)

    # Update pipeline entry stage if appropriate
    stmt_pe = select(PipelineEntry).where(PipelineEntry.id == msg.pipeline_entry_id)
    pe = db.execute(stmt_pe).scalar_one_or_none()
    if pe:
        pe.stage = "replied"

    write_audit(
        db=db,
        org_id=msg.org_id,
        actor_id=actor_id,
        action="reply_classified",
        entity="reply",
        entity_id=reply.id,
        payload={"intent": classification.intent, "priority": classification.priority}
    )

    db.commit()
    db.refresh(reply)
    return reply


def _get_reply(db: Session, reply_id: str, org_id: str) -> Reply:
    stmt = select(Reply).where(Reply.id == reply_id, Reply.org_id == org_id)
    reply = db.execute(stmt).scalar_one_or_none()
    if not reply:
        raise problem_detail_error(
            status_code=404,
            title="Reply not found",
            detail=f"Reply {reply_id} does not exist",
            code="REPLY_NOT_FOUND",
        )
    return reply


def _candidate_for_reply(db: Session, reply: Reply) -> Candidate:
    stmt = (
        select(Candidate)
        .join(PipelineEntry, PipelineEntry.candidate_id == Candidate.id)
        .join(OutreachMessage, OutreachMessage.pipeline_entry_id == PipelineEntry.id)
        .where(OutreachMessage.id == reply.outreach_message_id)
    )
    candidate = db.execute(stmt).scalar_one_or_none()
    if not candidate:
        raise problem_detail_error(
            status_code=404,
            title="Candidate not found",
            detail=f"No candidate resolves from reply {reply.id}",
            code="CANDIDATE_NOT_FOUND",
        )
    return candidate


async def classify_reply(db: Session, reply_id: str, user: User) -> Reply:
    """
    Re-run classification for an existing reply. Temperature 0.0, closed enum set.
    Classification NEVER triggers a send — it only labels.
    """
    reply = _get_reply(db, reply_id, user.org_id)

    stmt_msg = select(OutreachMessage).where(OutreachMessage.id == reply.outreach_message_id)
    msg = db.execute(stmt_msg).scalar_one_or_none()

    classification, _ = await run_structured(
        prompt_name="reply.v1",
        variables={
            "outreach_body": msg.body if msg else "",
            "reply_body": reply.raw_body,
        },
        schema=ReplyClassification,
        temperature=0.0,
    )

    reply.intent = classification.intent
    reply.sentiment = classification.sentiment
    reply.priority = classification.priority
    reply.summary = classification.summary
    reply.suggested_action = classification.suggested_action

    write_audit(
        db=db,
        org_id=reply.org_id,
        actor_id=user.id,
        action="reply_classified",
        entity="reply",
        entity_id=reply.id,
        payload={"intent": classification.intent, "priority": classification.priority},
    )
    db.commit()
    db.refresh(reply)
    return reply


async def draft_reply_response(db: Session, reply_id: str, user: User) -> Reply:
    """
    Generate a retrieval-gated response draft.

    The gate: if no knowledge chunk clears RESPONSE_MIN_RELEVANCE the model receives NO
    knowledge and is instructed to defer to the recruiter rather than answer. Compensation,
    benefits, policy and process questions therefore cannot be answered from inference.
    The result is always a DRAFT — it is never sent here.
    """
    reply = _get_reply(db, reply_id, user.org_id)

    knowledge_results = search_knowledge(
        db=db,
        org_id=reply.org_id,
        query=reply.raw_body,
        min_relevance=settings.RESPONSE_MIN_RELEVANCE,
    )

    retrieved_facts_text = ""
    used_chunks: list[str] = []
    if knowledge_results:
        retrieved_facts_text = "\n".join(f"[{c[0].id}] {c[0].content}" for c in knowledge_results)
        used_chunks = [c[0].id for c in knowledge_results]
    else:
        logger.info(
            "Retrieval gate closed for reply %s (no chunk >= %.2f) — model must defer.",
            reply.id, settings.RESPONSE_MIN_RELEVANCE,
        )

    response_draft, _ = await run_structured(
        prompt_name="respond.v1",
        variables={
            "reply_body": reply.raw_body,
            "classification": {
                "intent": reply.intent,
                "sentiment": reply.sentiment,
                "priority": reply.priority,
            },
            "knowledge_chunks": retrieved_facts_text,
        },
        schema=ResponseDraft,
        temperature=0.3,
    )

    draft = response_draft.model_dump()
    # The application, not the model, is the source of truth for what was actually retrieved.
    draft["knowledge_used"] = used_chunks
    draft["retrieval_gate_open"] = bool(used_chunks)

    reply.response_draft = draft
    reply.response_status = "draft"
    reply.response_approved_by = None
    reply.response_approved_at = None

    write_audit(
        db=db,
        org_id=reply.org_id,
        actor_id=user.id,
        action="response_drafted",
        entity="reply",
        entity_id=reply.id,
        payload={"knowledge_used": used_chunks, "gate_open": bool(used_chunks)},
    )
    db.commit()
    db.refresh(reply)
    return reply


def approve_reply_response(db: Session, reply_id: str, user: User) -> Reply:
    """Explicit human approval of a response draft. Separate call, separate audit entry."""
    reply = _get_reply(db, reply_id, user.org_id)

    if not reply.response_draft:
        raise problem_detail_error(
            status_code=409,
            title="No response draft",
            detail=f"Reply {reply_id} has no response draft to approve.",
            code="RESPONSE_NOT_DRAFTED",
        )
    if reply.response_status == "sent":
        raise problem_detail_error(
            status_code=409,
            title="Already sent",
            detail=f"Response for reply {reply_id} has already been sent.",
            code="RESPONSE_ALREADY_SENT",
        )

    reply.response_status = "approved"
    reply.response_approved_by = user.id
    reply.response_approved_at = utcnow()

    write_audit(
        db=db,
        org_id=reply.org_id,
        actor_id=user.id,
        action="response_approved",
        entity="reply",
        entity_id=reply.id,
        payload={"approved_by": user.id},
    )
    db.commit()
    db.refresh(reply)
    return reply


def send_reply_response(db: Session, reply_id: str, user: User) -> Reply:
    """
    Send an approved response. Two guards, in this order:
      1. require_response_approved -> 409 unless status == approved
      2. assert_contactable        -> 403, re-read fresh immediately before dispatch
    """
    reply = require_response_approved(db, reply_id)
    candidate = assert_contactable(db, _candidate_for_reply(db, reply).id)

    body = (reply.response_draft or {}).get("body", "")
    send_result = send_gmail_message(
        user=user,
        to_email=candidate.email,
        subject=f"Re: your reply",
        body=body,
    )

    reply.response_status = "sent"
    reply.response_sent_at = utcnow()

    write_audit(
        db=db,
        org_id=reply.org_id,
        actor_id=user.id,
        action="response_sent",
        entity="reply",
        entity_id=reply.id,
        payload={"to": candidate.email, "provider_id": send_result.get("id") if isinstance(send_result, dict) else None},
    )
    db.commit()
    db.refresh(reply)
    return reply


async def sync_gmail_replies(
    db: Session,
    user: User
) -> list[Reply]:
    """
    Syncs recent replies from Gmail (or fixture demo replies if simulated).
    """
    stmt = (
        select(OutreachMessage)
        .where(
            OutreachMessage.org_id == user.org_id,
            OutreachMessage.status == "sent"
        )
    )
    sent_messages = db.execute(stmt).scalars().all()

    created_replies = []
    # If no real messages or for demo seeding, process sent messages without replies
    for msg in sent_messages:
        stmt_rep = select(Reply).where(Reply.outreach_message_id == msg.id)
        if not db.execute(stmt_rep).scalar_one_or_none():
            # Generate simulated reply based on subject
            sample_body = "Hi, thanks for reaching out! I'd love to learn more about the technical stack and what the compensation range looks like for this role."
            reply = await process_incoming_reply(
                db=db,
                outreach_message_id=msg.id,
                raw_body=sample_body,
                actor_id=user.id
            )
            created_replies.append(reply)

    return created_replies
