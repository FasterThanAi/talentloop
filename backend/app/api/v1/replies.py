from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_scope
from app.models import Reply, User
from app.schemas.reply import ReplyOut, ReplySyncResponse
from app.services.conversation import (
    approve_reply_response,
    classify_reply,
    draft_reply_response,
    send_reply_response,
    sync_gmail_replies,
)

router = APIRouter(prefix="/replies", tags=["Replies"])


@router.get("", response_model=list[ReplyOut])
def list_replies(
    intent: str | None = Query(None),
    priority: str | None = Query(None),
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    stmt = select(Reply).where(Reply.org_id == current_user.org_id)
    if intent:
        stmt = stmt.where(Reply.intent == intent)
    if priority:
        stmt = stmt.where(Reply.priority == priority)

    stmt = stmt.order_by(Reply.received_at.desc())
    replies = db.execute(stmt).scalars().all()
    return [ReplyOut.model_validate(r) for r in replies]


@router.post("/sync", response_model=ReplySyncResponse)
async def sync_replies(
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    synced = await sync_gmail_replies(db=db, user=current_user)
    return ReplySyncResponse(
        synced_count=len(synced),
        classified_count=len(synced),
        replies=[ReplyOut.model_validate(r) for r in synced]
    )


@router.get("/{id}", response_model=ReplyOut)
def get_reply(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    stmt = select(Reply).where(Reply.id == id, Reply.org_id == current_user.org_id)
    reply = db.execute(stmt).scalar_one_or_none()
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")
    return ReplyOut.model_validate(reply)


@router.post("/{id}/classify", response_model=ReplyOut)
async def classify_reply_endpoint(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    """Re-classify a reply. Labels only — this never triggers a send."""
    reply = await classify_reply(db=db, reply_id=id, user=current_user)
    return ReplyOut.model_validate(reply)


@router.post("/{id}/draft-response", response_model=ReplyOut)
async def draft_response_endpoint(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    """
    Generate a retrieval-gated response draft. If no knowledge chunk clears the
    relevance threshold the draft defers to the recruiter instead of answering.
    """
    reply = await draft_reply_response(db=db, reply_id=id, user=current_user)
    return ReplyOut.model_validate(reply)


@router.post("/{id}/approve", response_model=ReplyOut)
def approve_response_endpoint(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    """Explicit human approval of the response draft (Invariant #2)."""
    reply = approve_reply_response(db=db, reply_id=id, user=current_user)
    return ReplyOut.model_validate(reply)


@router.post("/{id}/send", response_model=ReplyOut)
def send_response_endpoint(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    """
    Send the approved response. 409 unless response_status == 'approved';
    403 if the candidate is do-not-contact, re-checked immediately before dispatch.
    """
    reply = send_reply_response(db=db, reply_id=id, user=current_user)
    return ReplyOut.model_validate(reply)
