from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.deps import get_current_user, get_db, require_scope
from app.jobs.runner import enqueue_job
from app.models import PipelineEntry, Requisition, User
from app.schemas.ai import IdealProfile
from app.schemas.common import JobResponse
from app.schemas.feedback import BulkReleaseResponse
from app.schemas.requisition import RequisitionCreate, RequisitionOut, RequisitionUpdate
from app.services.feedback import bulk_release_feedback_reports
from app.services.outreach import bulk_send_approved_messages
from app.services.requisition import parse_requisition_jd, update_requisition_profile

router = APIRouter(prefix="/requisitions", tags=["Requisitions"])


@router.get("", response_model=List[RequisitionOut])
def list_requisitions(
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    stmt = (
        select(Requisition, func.count(PipelineEntry.id).label("candidate_count"))
        .outerjoin(PipelineEntry, Requisition.id == PipelineEntry.requisition_id)
        .where(Requisition.org_id == current_user.org_id)
        .group_by(Requisition.id)
        .order_by(Requisition.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    results = db.execute(stmt).all()
    output = []
    for req, count in results:
        req_out = RequisitionOut.model_validate(req)
        req_out.candidate_count = count
        output.append(req_out)
    return output


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
        status="active"
    )
    db.add(req)
    db.flush()

    write_audit(
        db=db,
        org_id=current_user.org_id,
        actor_id=current_user.id,
        action="requisition_created",
        entity="requisition",
        entity_id=req.id,
        payload={"title": req.title}
    )
    db.commit()
    db.refresh(req)
    return RequisitionOut.model_validate(req)


@router.get("/{id}", response_model=RequisitionOut)
def get_requisition(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    stmt = (
        select(Requisition, func.count(PipelineEntry.id).label("candidate_count"))
        .outerjoin(PipelineEntry, Requisition.id == PipelineEntry.requisition_id)
        .where(Requisition.id == id, Requisition.org_id == current_user.org_id)
        .group_by(Requisition.id)
    )
    row = db.execute(stmt).first()
    if not row:
        raise HTTPException(status_code=404, detail="Requisition not found")

    req, count = row
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
    req = update_requisition_profile(db=db, requisition_id=id, user=current_user, data=data)
    return RequisitionOut.model_validate(req)


@router.post("/{id}/parse", response_model=IdealProfile)
async def parse_jd(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    profile = await parse_requisition_jd(db=db, requisition_id=id, user=current_user)
    return profile


@router.post("/{id}/score", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def score_all_candidates(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    # Scoring compares a candidate against the ideal profile, so refuse the run rather than
    # queueing a job that can only fail per-entry.
    req = db.execute(
        select(Requisition).where(Requisition.id == id, Requisition.org_id == current_user.org_id)
    ).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")
    if not req.parsed_profile:
        raise HTTPException(
            status_code=400,
            detail={
                "type": "about:blank",
                "title": "Job description not parsed",
                "status": 400,
                "detail": (
                    "This requisition has no ideal profile yet. Open the requisition and run "
                    "'Parse Job Description' first — scoring has nothing to compare against "
                    "without it."
                ),
                "code": "PROFILE_NOT_PARSED",
            },
        )

    stmt = select(PipelineEntry.id).where(
        PipelineEntry.requisition_id == id,
        PipelineEntry.org_id == current_user.org_id
    )
    entry_ids = db.execute(stmt).scalars().all()
    if not entry_ids:
        raise HTTPException(
            status_code=400,
            detail={
                "type": "about:blank",
                "title": "No candidates to score",
                "status": 400,
                "detail": "No candidates found in this requisition pipeline. Source candidates first.",
                "code": "EMPTY_PIPELINE"
            }
        )

    job_id = await enqueue_job("score_candidates", {
        "org_id": current_user.org_id,
        "requisition_id": id,
        "pipeline_entry_ids": entry_ids,
        "actor_id": current_user.id,
        "total": len(entry_ids)
    })

    return JobResponse(job_id=job_id, status="queued", count=len(entry_ids))


@router.post("/{id}/send-approved")
def send_approved_outreach(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    result = bulk_send_approved_messages(db=db, requisition_id=id, user=current_user)
    return result


@router.post("/{id}/feedback/release-all", response_model=BulkReleaseResponse)
def release_all_non_shortlisted(
    id: str,
    threshold: int = Query(80),
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    return bulk_release_feedback_reports(db=db, requisition_id=id, threshold=threshold, user=current_user)
