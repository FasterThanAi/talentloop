from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class KnowledgeChunkCreate(BaseModel):
    source_type: str
    content: str
    document_id: str | None = None


class KnowledgeChunkOut(BaseModel):
    id: str
    org_id: str
    source_type: str
    content: str
    document_id: str | None = None
    chunk_index: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class CredentialVerifyResponse(BaseModel):
    payload_hash: str
    verified: bool
    network: str
    tx_hash: str | None = None
    revoked: bool
    issued_at: datetime | None = None
    details: dict[str, Any] | None = None


class InterviewAnswerSubmit(BaseModel):
    answers: dict[str, str]


class FollowUpAnswerSubmit(BaseModel):
    follow_up_answer: str


class InterviewSessionOut(BaseModel):
    id: str
    org_id: str
    pipeline_entry_id: str
    questions: list[dict[str, Any]]
    answers: dict[str, str]
    follow_up_question: str | None = None
    follow_up_answer: str | None = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
