from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_scope
from app.jobs.runner import enqueue_job
from app.models import Candidate, FeedbackReport, OutreachMessage, PipelineEntry, Requisition, User
from app.schemas.ai import IdealProfile
from app.schemas.feedback import BulkReleaseResponse
from app.schemas.outreach import BulkSendResult
from app.schemas.requisition import RequisitionCreate, RequisitionOut, RequisitionParseResponse, RequisitionUpdate
from app.services.feedback import bulk_release_feedback_reports
from app.services.outreach import bulk_send_approved_messages
from app.services.requisition import parse_and_update_requisition

router = APIRouter(prefix="/requisitions", tags=["Requisitions"])


@router.get("", response_model=list[RequisitionOut])
def list_requisitions(
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    stmt = (
        select(Requisition, func.count(PipelineEntry.id).label("candidate_count"))
        .outerjoin(PipelineEntry, Requisition.id == PipelineEntry.requisition_id)
        .where(Requisition.org_id == current_user.org_id)
        .group_by(Requisition.id)
        .order_by(Requisition.created_at.desc())
    )
    results = db.execute(stmt).all()
    out = []
    for req, count in results:
        req_out = RequisitionOut.model_validate(req)
        req_out.candidate_count = count
        out.append(req_out)
    return out


@router.post("", response_model=RequisitionOut, status_code=status.HTTP_201_CREATED)
def create_requisition(
    data: RequisitionCreate,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    req = Requisition(
        org_id=current_user.org_id,
        created_by=current_user.id,
        title=data.title,
        jd_raw=data.jd_raw,
        seniority=data.seniority,
        location=data.location,
        status="draft"
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return RequisitionOut.model_validate(req)


@router.get("/{id}", response_model=RequisitionOut)
def get_requisition(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    stmt = select(Requisition).where(Requisition.id == id, Requisition.org_id == current_user.org_id)
    req = db.execute(stmt).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")

    count = db.execute(
        select(func.count(PipelineEntry.id)).where(PipelineEntry.requisition_id == req.id)
    ).scalar() or 0

    req_out = RequisitionOut.model_validate(req)
    req_out.candidate_count = count
    return req_out


@router.put("/{id}", response_model=RequisitionOut)
def update_requisition(
    id: str,
    data: RequisitionUpdate,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    stmt = select(Requisition).where(Requisition.id == id, Requisition.org_id == current_user.org_id)
    req = db.execute(stmt).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")

    if data.title is not None:
        req.title = data.title
    if data.jd_raw is not None:
        req.jd_raw = data.jd_raw
    if data.parsed_profile is not None:
        req.parsed_profile = data.parsed_profile
    if data.seniority is not None:
        req.seniority = data.seniority
    if data.location is not None:
        req.location = data.location
    if data.status is not None:
        req.status = data.status

    db.commit()
    db.refresh(req)
    return RequisitionOut.model_validate(req)


@router.post("/{id}/parse", response_model=RequisitionParseResponse)
async def parse_requisition(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    req, profile, ai_meta = await parse_and_update_requisition(
        db=db,
        requisition_id=id,
        actor_id=current_user.id
    )
    return RequisitionParseResponse(
        requisition=RequisitionOut.model_validate(req),
        parsed_profile=profile,
        _ai=ai_meta
    )


@router.post("/{id}/score", status_code=status.HTTP_202_ACCEPTED)
async def score_requisition_candidates(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    # Fetch unscored pipeline entries for this requisition
    stmt = select(PipelineEntry).where(
        PipelineEntry.requisition_id == id,
        PipelineEntry.org_id == current_user.org_id
    )
    entries = db.execute(stmt).scalars().all()
    pe_ids = [pe.id for pe in entries]

    job_id = await enqueue_job("score_candidates", {
        "org_id": current_user.org_id,
        "requisition_id": id,
        "pipeline_ids": pe_ids,
        "actor_id": current_user.id,
        "total": len(pe_ids)
    })
    return {"job_id": job_id, "status": "queued", "total": len(pe_ids)}


@router.post("/{id}/send-approved", response_model=BulkSendResult)
def bulk_send(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    result = bulk_send_approved_messages(db=db, requisition_id=id, user=current_user)
    return BulkSendResult(**result)


@router.post("/{id}/feedback/release-all", response_model=BulkReleaseResponse)
def release_all_feedback(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    result = bulk_release_feedback_reports(db=db, requisition_id=id, user=current_user)
    return BulkReleaseResponse(**result)
