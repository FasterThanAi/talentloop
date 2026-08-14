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
    if not entity_id:
        # Almost always the same mistake: the caller did db.add(obj) and then passed obj.id
        # before flushing. SQLAlchemy applies the UUID column default at INSERT, not at
        # object construction, so obj.id is still None here. Left alone, this surfaces as an
        # opaque NotNullViolation at commit time and takes the whole request down. Fail here
        # instead, where the message names the fix.
        raise ValueError(
            f"write_audit({action!r}) received an empty entity_id for entity={entity!r}. "
            "If this is a newly created row, call db.flush() after db.add() so the primary "
            "key is populated before auditing."
        )

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
