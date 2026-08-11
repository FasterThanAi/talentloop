from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class CandidateCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    source: str = "manual"
    public_urls: List[str] = []


class CandidateResearchOut(BaseModel):
    id: str
    candidate_id: str
    summary: str
    skills: List[Dict[str, Any]]
    seniority_signals: List[Dict[str, Any]]
    projects: List[Dict[str, Any]]
    evidence_urls: List[str]
    confidence: str
    could_not_determine: List[str]
    researched_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateOut(BaseModel):
    id: str
    org_id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    source: str
    public_urls: List[str]
    consent_status: str
    do_not_contact: bool
    created_at: datetime
    research: Optional[CandidateResearchOut] = None

    model_config = ConfigDict(from_attributes=True)


class CandidateExportOut(BaseModel):
    candidate: CandidateOut
    research: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class CandidateDeleteResponse(BaseModel):
    status: str = "deleted"
    candidate_id: str
    tombstone_created: bool = True

    model_config = ConfigDict(from_attributes=True)


class SourcingURLsRequest(BaseModel):
    urls: List[str]
