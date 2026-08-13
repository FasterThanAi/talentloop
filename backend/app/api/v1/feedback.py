from typing import List

from app.schemas.credential import CredentialVerifyResponse
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_scope
from app.models import Candidate, CredentialRecord, FeedbackReport, PipelineEntry, Requisition, User
from app.schemas.feedback import FeedbackOut
from app.services.credential import issue_feedback_credential

router = APIRouter(tags=["Feedback & Portal"])


@router.get("/me/feedback", response_model=list[FeedbackOut])
def get_my_feedback_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Candidate portal: returns released feedback reports for the authenticated candidate user.
    """
    stmt_cand = select(Candidate).where(Candidate.email == current_user.email.lower())
    cand = db.execute(stmt_cand).scalar_one_or_none()
    if not cand:
        return []

    stmt = (
        select(FeedbackReport, Requisition.title, CredentialRecord.payload_hash)
        .join(PipelineEntry, FeedbackReport.pipeline_entry_id == PipelineEntry.id)
        .join(Requisition, PipelineEntry.requisition_id == Requisition.id)
        .outerjoin(CredentialRecord, FeedbackReport.id == CredentialRecord.feedback_report_id)
        .where(
            PipelineEntry.candidate_id == cand.id,
            FeedbackReport.released_at.is_not(None)
        )
        .order_by(FeedbackReport.released_at.desc())
    )
    results = db.execute(stmt).all()
    out = []
    for fb, role_title, cred_hash in results:
        item = FeedbackOut.model_validate(fb)
        item.role_title = role_title
        item.credential_hash = cred_hash
        out.append(item)
    return out


@router.post("/feedback/{id}/credential")
def issue_credential(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    record = issue_feedback_credential(db=db, feedback_report_id=id, actor_id=current_user.id)
    return {
        "payload_hash": record.payload_hash,
        "tx_hash": record.tx_hash,
        "network": record.network,
        "verification_url": f"/credentials/{record.payload_hash}/verify"
    }
