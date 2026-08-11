from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_scope
from app.models import OutreachMessage, User
from app.schemas.outreach import OutreachOut, OutreachUpdateRequest
from app.services.outreach import approve_outreach_message, send_outreach_message

router = APIRouter(prefix="/outreach", tags=["Outreach"])


@router.get("", response_model=list[OutreachOut])
def list_outreach(
    status_filter: str | None = Query(None, alias="status"),
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    stmt = select(OutreachMessage).where(OutreachMessage.org_id == current_user.org_id)
    if status_filter:
        stmt = stmt.where(OutreachMessage.status == status_filter)
    stmt = stmt.order_by(OutreachMessage.created_at.desc())
    messages = db.execute(stmt).scalars().all()
    return [OutreachOut.model_validate(m) for m in messages]


@router.get("/{id}", response_model=OutreachOut)
def get_outreach(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    stmt = select(OutreachMessage).where(OutreachMessage.id == id, OutreachMessage.org_id == current_user.org_id)
    msg = db.execute(stmt).scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Outreach message not found")
    return OutreachOut.model_validate(msg)


@router.put("/{id}", response_model=OutreachOut)
def update_outreach(
    id: str,
    data: OutreachUpdateRequest,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    stmt = select(OutreachMessage).where(OutreachMessage.id == id, OutreachMessage.org_id == current_user.org_id)
    msg = db.execute(stmt).scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Outreach message not found")

    if msg.status == "sent":
        raise HTTPException(status_code=400, detail="Cannot edit an outreach message that has already been sent.")

    if data.subject is not None:
        msg.subject = data.subject
    if data.body is not None:
        msg.body = data.body

    db.commit()
    db.refresh(msg)
    return OutreachOut.model_validate(msg)


@router.post("/{id}/approve", response_model=OutreachOut)
def approve_outreach(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    msg = approve_outreach_message(db=db, message_id=id, user=current_user)
    return OutreachOut.model_validate(msg)


@router.post("/{id}/send", response_model=OutreachOut)
def send_outreach(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    msg = send_outreach_message(db=db, message_id=id, user=current_user)
    return OutreachOut.model_validate(msg)
