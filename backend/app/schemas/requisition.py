from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.schemas.ai import IdealProfile


class RequisitionCreate(BaseModel):
    title: str
    jd_raw: str
    seniority: str | None = None
    location: str | None = None


class RequisitionUpdate(BaseModel):
    title: str | None = None
    jd_raw: str | None = None
    parsed_profile: dict[str, Any] | None = None
    seniority: str | None = None
    location: str | None = None
    status: str | None = None


class RequisitionOut(BaseModel):
    id: str
    org_id: str
    created_by: str
    title: str
    jd_raw: str
    parsed_profile: dict[str, Any] | None = None
    seniority: str | None = None
    location: str | None = None
    status: str
    rizeos_job_id: str | None = None
    created_at: datetime
    candidate_count: int | None = 0

    class Config:
        from_attributes = True


class RequisitionParseResponse(BaseModel):
    requisition: RequisitionOut
    parsed_profile: IdealProfile
    _ai: dict[str, Any] | None = None
