from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, get_db, require_scope
from app.jobs.scoring import score_pipeline_entry
from app.models import Candidate, CandidateResearch, FeedbackReport, PipelineEntry, Requisition, User
from app.schemas.ai import ScoreBreakdown
from app.schemas.feedback import FeedbackOut
from app.schemas.outreach import OutreachOut
from app.schemas.pipeline import PipelineEntryOut, PipelineExplainOut
from app.services.feedback import generate_feedback_report, release_feedback_report
from app.services.interview import generate_interview_questions
from app.services.outreach import draft_outreach_message

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


@router.get("", response_model=list[PipelineEntryOut])
def list_pipeline_entries(
    requisition_id: str | None = Query(None),
    stage: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    stmt = (
        select(PipelineEntry)
        .options(joinedload(PipelineEntry.candidate).joinedload(Candidate.research))
        .where(PipelineEntry.org_id == current_user.org_id)
    )
    if requisition_id:
        stmt = stmt.where(PipelineEntry.requisition_id == requisition_id)
    if stage:
        stmt = stmt.where(PipelineEntry.stage == stage)

    stmt = stmt.order_by(PipelineEntry.fit_score.desc().nullslast(), PipelineEntry.created_at.desc()).limit(limit).offset(offset)
    entries = db.execute(stmt).scalars().unique().all()
    return [PipelineEntryOut.model_validate(e) for e in entries]


@router.get("/{id}", response_model=PipelineEntryOut)
def get_pipeline_entry(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    stmt = (
        select(PipelineEntry)
        .options(joinedload(PipelineEntry.candidate).joinedload(Candidate.research))
        .where(PipelineEntry.id == id, PipelineEntry.org_id == current_user.org_id)
    )
    entry = db.execute(stmt).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Pipeline entry not found")
    return PipelineEntryOut.model_validate(entry)


@router.get("/{id}/explain", response_model=PipelineExplainOut)
def explain_fit_score(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    stmt = (
        select(PipelineEntry)
        .options(joinedload(PipelineEntry.candidate).joinedload(Candidate.research))
        .where(PipelineEntry.id == id, PipelineEntry.org_id == current_user.org_id)
    )
    entry = db.execute(stmt).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Pipeline entry not found")

    req = db.execute(select(Requisition).where(Requisition.id == entry.requisition_id)).scalar_one_or_none()
    breakdown_obj = ScoreBreakdown.model_validate(entry.score_breakdown) if entry.score_breakdown else None

    evidence_urls = []
    if entry.candidate and entry.candidate.research:
        evidence_urls = entry.candidate.research.evidence_urls or []

    return PipelineExplainOut(
        pipeline_entry_id=entry.id,
        candidate_name=entry.candidate.full_name if entry.candidate else "Candidate",
        role_title=req.title if req else "Role",
        fit_score=entry.fit_score,
        score_reason=entry.score_reason,
        breakdown=breakdown_obj,
        rubric_version=entry.rubric_version,
        confidence=breakdown_obj.confidence if breakdown_obj else "medium",
        could_not_determine=breakdown_obj.could_not_determine if breakdown_obj else [],
        risk_flags=breakdown_obj.risk_flags if breakdown_obj else [],
        evidence_urls=evidence_urls
    )


@router.post("/{id}/score", response_model=PipelineEntryOut)
async def score_entry(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    entry = await score_pipeline_entry(db=db, pipeline_entry_id=id, actor_id=current_user.id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry could not be scored")
    return PipelineEntryOut.model_validate(entry)


@router.post("/{id}/draft", response_model=OutreachOut)
async def draft_outreach(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    msg = await draft_outreach_message(db=db, pipeline_entry_id=id, actor_id=current_user.id)
    return OutreachOut.model_validate(msg)


@router.post("/{id}/feedback/generate", response_model=FeedbackOut)
async def generate_feedback(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    fb = await generate_feedback_report(db=db, pipeline_entry_id=id, actor_id=current_user.id)
    return FeedbackOut.model_validate(fb)


@router.get("/{id}/feedback", response_model=FeedbackOut)
def get_feedback(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    stmt = select(FeedbackReport).where(FeedbackReport.pipeline_entry_id == id)
    fb = db.execute(stmt).scalar_one_or_none()
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback report not found")
    return FeedbackOut.model_validate(fb)


@router.post("/{id}/feedback/release", response_model=FeedbackOut)
def release_feedback(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    fb = release_feedback_report(db=db, pipeline_entry_id=id, user=current_user)
    return FeedbackOut.model_validate(fb)


@router.post("/{id}/interview/generate")
async def generate_interview(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    sess = await generate_interview_questions(db=db, pipeline_entry_id=id)
    return {"interview_session_id": sess.id, "questions": sess.questions, "status": sess.status}
