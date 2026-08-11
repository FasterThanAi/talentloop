from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_scope
from app.models import AuditEvent, User
from app.schemas.audit import AuditEventOut

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("", response_model=list[AuditEventOut])
def list_audit_events(
    entity: str | None = Query(None),
    entity_id: str | None = Query(None),
    limit: int = Query(100, le=500),
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    stmt = select(AuditEvent).where(AuditEvent.org_id == current_user.org_id)
    if entity:
        stmt = stmt.where(AuditEvent.entity == entity)
    if entity_id:
        stmt = stmt.where(AuditEvent.entity_id == entity_id)

    stmt = stmt.order_by(AuditEvent.created_at.desc()).limit(limit)
    events = db.execute(stmt).scalars().all()
    return [AuditEventOut.model_validate(e) for e in events]
