from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import problem_detail_error
from app.models import Candidate, OutreachMessage


def assert_contactable(db: Session, candidate_id: str) -> Candidate:
    """
    Middleware/Service-level guard checking do_not_contact immediately before any outbound action.
    This check is non-bypassable and re-reads fresh state from DB.
    """
    stmt = select(Candidate).where(Candidate.id == candidate_id)
    candidate = db.execute(stmt).scalar_one_or_none()

    if not candidate:
        raise problem_detail_error(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Candidate not found",
            detail=f"Candidate {candidate_id} does not exist",
            code="CANDIDATE_NOT_FOUND"
        )

    if candidate.do_not_contact:
        raise problem_detail_error(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Candidate do-not-contact active",
            detail=f"Candidate {candidate_id} has activated do-not-contact. All outbound actions are blocked.",
            code="CANDIDATE_DO_NOT_CONTACT"
        )

    return candidate


def require_approved(db: Session, message_id: str) -> OutreachMessage:
    """
    Middleware/Service-level guard enforcing Invariant #2:
    Nothing reaches a human without explicit approval.
    """
    stmt = select(OutreachMessage).where(OutreachMessage.id == message_id)
    message = db.execute(stmt).scalar_one_or_none()

    if not message:
        raise problem_detail_error(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Outreach message not found",
            detail=f"Message {message_id} does not exist",
            code="OUTREACH_NOT_FOUND"
        )

    if message.status != "approved":
        raise problem_detail_error(
            status_code=status.HTTP_409_CONFLICT,
            title="Draft not approved",
            detail=f"Message {message_id} is in state '{message.status}'. Approve it before sending.",
            code="OUTREACH_NOT_APPROVED"
        )

    return message
