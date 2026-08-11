from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr


class CandidateCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    source: str = "manual"
    public_urls: list[str] = []


class CandidateResearchOut(BaseModel):
    id: str
    candidate_id: str
    summary: str
    skills: list[dict[str, Any]]
    seniority_signals: list[dict[str, Any]]
    projects: list[dict[str, Any]]
    evidence_urls: list[str]
    confidence: str
    could_not_determine: list[str]
    researched_at: datetime

    class Config:
        from_attributes = True


class CandidateOut(BaseModel):
    id: str
    org_id: str
    full_name: str
    email: str
    phone: str | None = None
    source: str
    public_urls: list[str]
    consent_status: str
    do_not_contact: bool
    created_at: datetime
    research: CandidateResearchOut | None = None

    class Config:
        from_attributes = True


class SourcingURLsRequest(BaseModel):
    urls: list[str]
