from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models import AuditEvent


def write_audit(
    db: Session,
    org_id: str,
    actor_id: str,
    action: str,
    entity: str,
    entity_id: str,
    payload: dict[str, Any] | None = None
) -> AuditEvent:
    """
    Append-only audit logger.
    Executed inside the caller's active database transaction so that
    the action and its audit row commit or roll back together.
    """
    event = AuditEvent(
        org_id=org_id,
        actor_id=actor_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        payload=payload or {}
    )
    db.add(event)
    return event
