from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ReplyOut(BaseModel):
    id: str
    org_id: str
    outreach_message_id: str
    raw_body: str
    intent: str
    sentiment: str
    priority: str
    summary: str
    suggested_action: str
    response_draft: dict[str, Any] | None = None
    received_at: datetime

    class Config:
        from_attributes = True


class ReplySyncResponse(BaseModel):
    synced_count: int
    classified_count: int
    replies: list[ReplyOut]
