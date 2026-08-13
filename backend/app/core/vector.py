"""
Dialect-aware vector storage.

The product claims Supabase PostgreSQL + pgvector, and on Postgres that is exactly what
runs: a real `vector(N)` column with an ivfflat cosine index and `<=>` distance search.
SQLite is supported as a local-dev fallback only — the same embeddings are stored as JSON
and cosine similarity is computed in Python, so behaviour is identical and only the
performance characteristics differ.

Nothing here silently degrades: `vector_backend()` reports which mode is live and the
/health endpoint surfaces it.
"""
from __future__ import annotations

import logging
import math
from typing import Any

from sqlalchemy import JSON
from sqlalchemy.types import TypeDecorator

from app.core.config import settings

logger = logging.getLogger("talentloop.vector")

IS_POSTGRES = settings.DATABASE_URL.startswith(("postgresql", "postgres://"))

try:  # pgvector is only importable when installed; absence must not break SQLite dev
    from pgvector.sqlalchemy import Vector as _PGVector  # type: ignore
    PGVECTOR_AVAILABLE = True
except Exception:  # pragma: no cover - depends on environment
    _PGVector = None  # type: ignore
    PGVECTOR_AVAILABLE = False


def vector_backend() -> str:
    """One of: 'pgvector', 'json-cosine'. Reported by /health so it is never ambiguous."""
    if IS_POSTGRES and PGVECTOR_AVAILABLE:
        return "pgvector"
    return "json-cosine"


class EmbeddingColumn(TypeDecorator):
    """
    Stores an embedding as `vector(N)` on PostgreSQL and as JSON everywhere else.

    Using a TypeDecorator (rather than two model definitions) means the ORM layer is
    identical in both modes and only the DDL differs.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and PGVECTOR_AVAILABLE:
            return dialect.type_descriptor(_PGVector(settings.EMBEDDING_DIMENSION))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Any, dialect):
        if value is None:
            return None
        return list(value)

    def process_result_value(self, value: Any, dialect):
        if value is None:
            return None
        return list(value)


def cosine_similarity(a: list[float] | None, b: list[float] | None) -> float:
    """Pure-python cosine similarity, used by the json-cosine backend."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
