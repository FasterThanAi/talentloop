from fastapi import APIRouter
from pydantic import BaseModel

from app.ai.client import ai_is_mocked
from app.core.config import settings
from app.core.db import check_db_connection, check_pgvector_extension
from app.core.vector import vector_backend

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    db: bool
    pgvector: bool
    version: str = "0.1.0"
    # Operational honesty: these three make it impossible to demo on mocks by accident.
    db_dialect: str
    vector_backend: str
    ai_mode: str


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def get_health() -> HealthResponse:
    db_ok = check_db_connection()
    pgvector_ok = check_pgvector_extension()
    mocked = ai_is_mocked()
    dialect = "postgresql" if settings.DATABASE_URL.startswith(("postgresql", "postgres://")) else "sqlite"

    status = "ok"
    if not db_ok:
        status = "degraded"
    elif mocked:
        status = "mock-ai"

    return HealthResponse(
        status=status,
        db=db_ok,
        pgvector=pgvector_ok,
        version="0.1.0",
        db_dialect=dialect,
        vector_backend=vector_backend(),
        ai_mode="MOCK" if mocked else settings.GEMINI_MODEL,
    )
