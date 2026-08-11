import logging
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.runner import run_structured
from app.core.deps import problem_detail_error
from app.models import FeedbackReport, InterviewSession, PipelineEntry, Requisition
from app.schemas.ai import FollowUpQuestion, InterviewQuestions

logger = logging.getLogger("talentloop.interview")


async def generate_interview_questions(
    db: Session,
    pipeline_entry_id: str
) -> InterviewSession:
    stmt = select(PipelineEntry).where(PipelineEntry.id == pipeline_entry_id)
    pe = db.execute(stmt).scalar_one_or_none()
    if not pe:
        raise problem_detail_error(status_code=404, title="Not found", detail="Pipeline entry not found", code="PIPELINE_ENTRY_NOT_FOUND")

    stmt_req = select(Requisition).where(Requisition.id == pe.requisition_id)
    req = db.execute(stmt_req).scalar_one_or_none()

    stmt_fb = select(FeedbackReport).where(FeedbackReport.pipeline_entry_id == pe.id)
    fb = db.execute(stmt_fb).scalar_one_or_none()

    gaps = fb.gaps if fb and fb.gaps else []

    questions_res, _ = await run_structured(
        prompt_name="interview.v1",
        variables={
            "ideal_profile": req.parsed_profile if req else {},
            "named_gaps": gaps
        },
        schema=InterviewQuestions,
        temperature=0.3
    )

    stmt_sess = select(InterviewSession).where(InterviewSession.pipeline_entry_id == pe.id)
    sess = db.execute(stmt_sess).scalar_one_or_none()

    if not sess:
        sess = InterviewSession(
            org_id=pe.org_id,
            pipeline_entry_id=pe.id,
            questions=[q.model_dump() for q in questions_res.questions],
            answers={},
            status="pending"
        )
        db.add(sess)
    else:
        sess.questions = [q.model_dump() for q in questions_res.questions]

    db.commit()
    db.refresh(sess)
    return sess
