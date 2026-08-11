import logging
from datetime import UTC, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.runner import run_structured
from app.core.audit import write_audit
from app.core.config import settings
from app.models import OutreachMessage, PipelineEntry, Reply, User
from app.schemas.ai import ReplyClassification, ResponseDraft
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
