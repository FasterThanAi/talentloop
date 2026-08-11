import logging
from datetime import UTC, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.runner import run_structured
from app.core.audit import write_audit
from app.core.deps import problem_detail_error
from app.core.guards import assert_contactable
from app.models import Candidate, FeedbackReport, PipelineEntry, Requisition, User
from app.schemas.ai import FeedbackReport as FeedbackReportSchema

logger = logging.getLogger("talentloop.feedback")


def utcnow() -> datetime:
    return datetime.now(UTC)


async def generate_feedback_report(
    db: Session,
    pipeline_entry_id: str,
    actor_id: str
) -> FeedbackReport:
    stmt = select(PipelineEntry).where(PipelineEntry.id == pipeline_entry_id)
    pe = db.execute(stmt).scalar_one_or_none()
    if not pe or not pe.score_breakdown:
        raise problem_detail_error(
            status_code=400,
            title="Candidate unscored",
            detail="Cannot generate feedback for a candidate without an existing scored rubric breakdown.",
            code="CANDIDATE_NOT_SCORED"
        )

    stmt_req = select(Requisition).where(Requisition.id == pe.requisition_id)
    req = db.execute(stmt_req).scalar_one_or_none()
    role_title = req.title if req else "Role"

    # Invariant: Prompt receives ONLY the validated breakdown (no candidate name, no raw evidence)
    report_data, _ = await run_structured(
        prompt_name="feedback.v1",
        variables={
            "role_title": role_title,
            "score_breakdown": pe.score_breakdown
        },
        schema=FeedbackReportSchema,
        temperature=0.4
    )

    stmt_fb = select(FeedbackReport).where(FeedbackReport.pipeline_entry_id == pe.id)
    fb = db.execute(stmt_fb).scalar_one_or_none()

    if not fb:
        fb = FeedbackReport(
            org_id=pe.org_id,
            pipeline_entry_id=pe.id,
            fit_summary=report_data.fit_summary,
            strengths=[s.model_dump() for s in report_data.strengths],
            gaps=[g.model_dump() for g in report_data.gaps],
            improve_advice=report_data.improve_advice,
            score_snapshot=pe.fit_score or 0,
            released_at=None
        )
        db.add(fb)
    else:
        fb.fit_summary = report_data.fit_summary
        fb.strengths = [s.model_dump() for s in report_data.strengths]
        fb.gaps = [g.model_dump() for g in report_data.gaps]
        fb.improve_advice = report_data.improve_advice
        fb.score_snapshot = pe.fit_score or 0

    write_audit(
        db=db,
        org_id=pe.org_id,
        actor_id=actor_id,
        action="feedback_generated",
        entity="feedback_report",
        entity_id=fb.id,
        payload={"score_snapshot": fb.score_snapshot, "role_title": role_title}
    )

    db.commit()
    db.refresh(fb)
    return fb


def release_feedback_report(
    db: Session,
    pipeline_entry_id: str,
    user: User
) -> FeedbackReport:
    stmt = select(PipelineEntry).where(PipelineEntry.id == pipeline_entry_id)
    pe = db.execute(stmt).scalar_one_or_none()
    if not pe:
        raise problem_detail_error(status_code=404, title="Not found", detail="Pipeline entry not found", code="PIPELINE_ENTRY_NOT_FOUND")

    # Guard check: Must be contactable
    assert_contactable(db, pe.candidate_id)

    stmt_fb = select(FeedbackReport).where(FeedbackReport.pipeline_entry_id == pe.id)
    fb = db.execute(stmt_fb).scalar_one_or_none()
    if not fb:
        raise problem_detail_error(status_code=404, title="Report not found", detail="Feedback report not yet generated", code="FEEDBACK_NOT_FOUND")

    fb.released_at = utcnow()

    write_audit(
        db=db,
        org_id=pe.org_id,
        actor_id=user.id,
        action="feedback_released",
        entity="feedback_report",
        entity_id=fb.id,
        payload={"released_by": user.email, "timestamp": fb.released_at.isoformat()}
    )

    db.commit()
    db.refresh(fb)
    return fb


def bulk_release_feedback_reports(
    db: Session,
    requisition_id: str,
    user: User
) -> dict[str, Any]:
    stmt = (
        select(FeedbackReport)
        .join(PipelineEntry, FeedbackReport.pipeline_entry_id == PipelineEntry.id)
        .where(
            PipelineEntry.requisition_id == requisition_id,
            FeedbackReport.released_at.is_(None)
        )
    )
    reports = db.execute(stmt).scalars().all()

    released_ids = []
    for fb in reports:
        stmt_pe = select(PipelineEntry).where(PipelineEntry.id == fb.pipeline_entry_id)
        pe = db.execute(stmt_pe).scalar_one_or_none()
        if pe:
            try:
                assert_contactable(db, pe.candidate_id)
                fb.released_at = utcnow()
                write_audit(
                    db=db,
                    org_id=pe.org_id,
                    actor_id=user.id,
                    action="feedback_released",
                    entity="feedback_report",
                    entity_id=fb.id,
                    payload={"bulk": True, "released_by": user.email}
                )
                released_ids.append(fb.id)
            except Exception as e:
                logger.warning(f"Skipping feedback release for candidate {pe.candidate_id}: {e}")

    db.commit()
    return {"released_count": len(released_ids), "pipeline_ids": released_ids}
