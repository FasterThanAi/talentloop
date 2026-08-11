from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_scope
from app.models import Reply, User
from app.schemas.reply import ReplyOut, ReplySyncResponse
from app.services.conversation import sync_gmail_replies

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
