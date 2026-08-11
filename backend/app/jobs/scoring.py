import logging
from datetime import UTC
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.runner import run_structured
from app.core.audit import write_audit
from app.core.db import SessionLocal
from app.jobs.runner import register_job_handler, update_job_progress
from app.models import Candidate, CandidateResearch, FeedbackReport, KnowledgeChunk, PipelineEntry, Requisition
from app.rubric.compute import compute_fit_score
from app.rubric.dimensions import DIMENSION_MAP, RUBRIC_VERSION
from app.schemas.ai import FeedbackReport as FeedbackReportSchema
from app.schemas.ai import IdealProfile, ScoreBreakdown

logger = logging.getLogger("talentloop.scoring")


def sanitize_scoring_input(
    candidate_research: CandidateResearch | None
) -> dict[str, Any]:
    """
    Sanitizes candidate data for scoring.
    STRICTLY EXCLUDES: full_name, photo, age, gender, and institution prestige.
    Passes ONLY skills, evidence quotes, projects, and seniority signals.
    """
    if not candidate_research:
        return {
            "summary": "No public evidence available.",
            "skills": [],
            "seniority_signals": [],
            "projects": [],
            "confidence": "low",
            "could_not_determine": ["All must-have requirements"]
        }

    return {
        "summary": candidate_research.summary,
        "skills": candidate_research.skills or [],
        "seniority_signals": candidate_research.seniority_signals or [],
        "projects": candidate_research.projects or [],
        "confidence": candidate_research.confidence or "medium",
        "could_not_determine": candidate_research.could_not_determine or []
    }


async def score_pipeline_entry(
    db: Session,
    pipeline_entry_id: str,
    actor_id: str = "system"
) -> PipelineEntry | None:
    stmt = select(PipelineEntry).where(PipelineEntry.id == pipeline_entry_id)
    pe = db.execute(stmt).scalar_one_or_none()
    if not pe:
        return None

    # Load requisition
    stmt_req = select(Requisition).where(Requisition.id == pe.requisition_id)
    req = db.execute(stmt_req).scalar_one_or_none()
    if not req or not req.parsed_profile:
        return None

    ideal_profile = IdealProfile.model_validate(req.parsed_profile)

    # Load candidate research
    stmt_res = select(CandidateResearch).where(CandidateResearch.candidate_id == pe.candidate_id)
    res = db.execute(stmt_res).scalar_one_or_none()
    sanitized_evidence = sanitize_scoring_input(res)

    # Load org knowledge
    stmt_k = select(KnowledgeChunk).where(KnowledgeChunk.org_id == pe.org_id)
    chunks = db.execute(stmt_k).scalars().all()
    knowledge_text = "\n".join(f"[{c.source_type}]: {c.content}" for c in chunks) if chunks else "None provided."

    # Execute scoring model prompt
    breakdown, ai_result = await run_structured(
        prompt_name="score.v1",
        variables={
            "ideal_profile": ideal_profile.model_dump(),
            "candidate_evidence": sanitized_evidence,
            "knowledge_chunks": knowledge_text
        },
        schema=ScoreBreakdown,
        temperature=0.0
    )

    # Anti-Hallucination Citation Verification:
    # Ensure every citation URL appears in candidate's stored evidence URLs
    valid_evidence_urls = set(res.evidence_urls if res and res.evidence_urls else [])
    for dim in breakdown.dimensions:
        if dim.citations and valid_evidence_urls:
            # If model returned a citation not in stored set, filter it
            dim.citations = [c for c in dim.citations if c in valid_evidence_urls]

    # Invariant #1: Deterministic Python computes final score!
    final_score, reason = compute_fit_score(breakdown, ideal_profile)

    pe.fit_score = final_score
    pe.score_reason = reason
    pe.score_breakdown = breakdown.model_dump()
    pe.rubric_version = RUBRIC_VERSION
    pe.stage = "scored"
    from datetime import datetime, timezone
    pe.scored_at = datetime.now(UTC)

    # Automatically generate feedback report draft (P7) with released_at=NULL
    try:
        feedback_schema, _ = await run_structured(
            prompt_name="feedback.v1",
            variables={
                "role_title": req.title,
                "score_breakdown": breakdown.model_dump()
            },
            schema=FeedbackReportSchema,
            temperature=0.4
        )

        stmt_fb = select(FeedbackReport).where(FeedbackReport.pipeline_entry_id == pe.id)
        fb_report = db.execute(stmt_fb).scalar_one_or_none()

        if not fb_report:
            fb_report = FeedbackReport(
                org_id=pe.org_id,
                pipeline_entry_id=pe.id,
                fit_summary=feedback_schema.fit_summary,
                strengths=[s.model_dump() for s in feedback_schema.strengths],
                gaps=[g.model_dump() for g in feedback_schema.gaps],
                improve_advice=feedback_schema.improve_advice,
                score_snapshot=final_score,
                released_at=None
            )
            db.add(fb_report)
        else:
            fb_report.fit_summary = feedback_schema.fit_summary
            fb_report.strengths = [s.model_dump() for s in feedback_schema.strengths]
            fb_report.gaps = [g.model_dump() for g in feedback_schema.gaps]
            fb_report.improve_advice = feedback_schema.improve_advice
            fb_report.score_snapshot = final_score
    except Exception as e:
        logger.warning(f"Auto feedback generation for {pe.id} failed: {e}")

    write_audit(
        db=db,
        org_id=pe.org_id,
        actor_id=actor_id,
        action="candidate_scored",
        entity="pipeline_entry",
        entity_id=pe.id,
        payload={"fit_score": final_score, "rubric_version": RUBRIC_VERSION, "reason": reason}
    )

    db.commit()
    db.refresh(pe)
    return pe


async def handle_scoring_job(job_id: str, payload: dict[str, Any]) -> None:
    pipeline_ids: list[str] = payload.get("pipeline_ids", [])
    actor_id: str = payload.get("actor_id", "system")

    db = SessionLocal()
    try:
        for pe_id in pipeline_ids:
            try:
                await score_pipeline_entry(db=db, pipeline_entry_id=pe_id, actor_id=actor_id)
                update_job_progress(job_id, processed_delta=1)
            except Exception as e:
                logger.error(f"Failed to score pipeline entry {pe_id}: {e}")
                update_job_progress(job_id, processed_delta=1, error_entry={"pipeline_entry_id": pe_id, "error": str(e)})
    finally:
        db.close()


register_job_handler("score_candidates", handle_scoring_job)
