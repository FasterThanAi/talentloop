from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class AIMetadataOut(BaseModel):
    model: str
    prompt: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0

    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    next_cursor: Optional[str] = None
    total: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class JobResponse(BaseModel):
    job_id: str
    status: str = "queued"
    count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
