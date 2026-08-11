from fastapi import APIRouter
from pydantic import BaseModel

from app.core.db import check_db_connection, check_pgvector_extension

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    db: bool
    pgvector: bool
    version: str = "0.1.0"


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def get_health() -> HealthResponse:
    db_ok = check_db_connection()
    pgvector_ok = check_pgvector_extension()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        db=db_ok,
        pgvector=pgvector_ok,
        version="0.1.0"
    )
