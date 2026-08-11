from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class OutreachDraftRequest(BaseModel):
    pipeline_entry_id: str


class OutreachUpdateRequest(BaseModel):
    subject: str | None = None
    body: str | None = None


class OutreachOut(BaseModel):
    id: str
    org_id: str
    pipeline_entry_id: str
    channel: str
    subject: str
    body: str
    status: str
    approved_by: str | None = None
    approved_at: datetime | None = None
    sent_at: datetime | None = None
    gmail_message_id: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class BulkSendResult(BaseModel):
    sent_count: int
    failed_count: int
    results: list[dict[str, Any]]
