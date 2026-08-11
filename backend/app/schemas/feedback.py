from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class FeedbackOut(BaseModel):
    id: str
    org_id: str
    pipeline_entry_id: str
    fit_summary: str
    strengths: list[dict[str, Any]]
    gaps: list[dict[str, Any]]
    improve_advice: list[str]
    score_snapshot: int
    released_at: datetime | None = None
    candidate_seen_at: datetime | None = None
    created_at: datetime
    role_title: str | None = None
    credential_hash: str | None = None

    class Config:
        from_attributes = True


class BulkReleaseResponse(BaseModel):
    released_count: int
    pipeline_ids: list[str]
