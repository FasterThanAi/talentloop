from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class AuditEventOut(BaseModel):
    id: str
    org_id: str
    actor_id: str
    action: str
    entity: str
    entity_id: str
    payload: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
