from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.schemas.ai import ScoreBreakdown
from app.schemas.candidate import CandidateOut


class PipelineEntryOut(BaseModel):
    id: str
    org_id: str
    requisition_id: str
    candidate_id: str
    stage: str
    fit_score: int | None = None
    score_reason: str | None = None
    score_breakdown: dict[str, Any] | None = None
    rubric_version: str | None = None
    scored_at: datetime | None = None
    created_at: datetime
    candidate: CandidateOut | None = None

    class Config:
        from_attributes = True


class PipelineExplainOut(BaseModel):
    pipeline_entry_id: str
    candidate_name: str
    role_title: str
    fit_score: int | None
    score_reason: str | None
    breakdown: ScoreBreakdown | None
    rubric_version: str | None
    confidence: str | None
    could_not_determine: list[str] = []
    risk_flags: list[str] = []
    evidence_urls: list[str] = []
