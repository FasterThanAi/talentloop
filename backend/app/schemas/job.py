from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class JobOut(BaseModel):
    id: str
    org_id: str
    name: str
    status: str
    processed: int
    total: int
    errors: list[dict[str, Any]]
    result_ref: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
