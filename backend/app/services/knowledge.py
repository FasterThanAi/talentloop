"""
Hybrid retrieval over verified company knowledge.

Semantic retrieval first (pgvector `<=>` on Postgres, python cosine on SQLite), merged
with keyword overlap, deduplicated, and filtered by a relevance floor. If embeddings are
unavailable for any reason the search degrades to keyword-only rather than failing — but
it says so in the returned mode, because a silent degrade in a retrieval-gated system
would let the model answer from nothing.
"""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import engine
from app.core.vector import IS_POSTGRES, PGVECTOR_AVAILABLE, cosine_similarity, vector_backend
from app.models import KnowledgeChunk

logger = logging.getLogger("talentloop.knowledge")

# Weighting when both signals are present.
SEMANTIC_WEIGHT = 0.7
KEYWORD_WEIGHT = 0.3


def compute_keyword_overlap_score(query: str, text_value: str) -> float:
    q_words = {w.strip(".,?!:;()").lower() for w in query.split() if len(w) > 2}
    t_words = {w.strip(".,?!:;()").lower() for w in text_value.split() if len(w) > 2}
    if not q_words or not t_words:
        return 0.0
    overlap = q_words.intersection(t_words)
    return len(overlap) / max(1, len(q_words))


async def embed_text(content: str) -> list[float] | None:
    """
    Generate an embedding via the configured Gemini embedding model.
    Returns None (not an exception) when embeddings are unavailable, so callers can
    fall back to keyword search rather than losing the write.
    """
    try:
        from app.ai.client import ai_client
        return await ai_client.embed(content)
    except Exception as e:  # pragma: no cover - network/config dependent
        logger.warning("Embedding generation failed, falling back to keyword-only: %s", e)
        return None


async def embed_missing_chunks(db: Session, org_id: str, limit: int = 200) -> int:
    """Backfill embeddings for chunks that have none. Returns the number embedded."""
    stmt = (
        select(KnowledgeChunk)
        .where(KnowledgeChunk.org_id == org_id, KnowledgeChunk.embedding.is_(None))
        .limit(limit)
    )
    chunks = db.execute(stmt).scalars().all()
    embedded = 0
    for chunk in chunks:
        vec = await embed_text(chunk.content)
        if vec:
            chunk.embedding = vec
            embedded += 1
            db.commit()  # commit per item so a failure never loses the batch
    return embedded


def _semantic_candidates_postgres(
    db: Session, org_id: str, query_vec: list[float], limit: int
) -> list[tuple[str, float]]:
    """pgvector cosine distance search. Returns (chunk_id, similarity)."""
    sql = text(
        """
        SELECT id, 1 - (embedding <=> CAST(:qv AS vector)) AS similarity
        FROM knowledge_chunks
        WHERE org_id = :org_id AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:qv AS vector)
        LIMIT :limit
        """
    )
    rows = db.execute(
        sql, {"qv": str(query_vec), "org_id": org_id, "limit": limit}
    ).fetchall()
    return [(r[0], float(r[1])) for r in rows]


def search_knowledge(
    db: Session,
    org_id: str,
    query: str,
    min_relevance: float = 0.50,
    limit: int = 3,
    query_embedding: list[float] | None = None,
) -> list[tuple[KnowledgeChunk, float]]:
    """
    Hybrid search. Returns [(chunk, score)] sorted desc, filtered to score >= min_relevance.

    An empty result is a meaningful signal: it closes the retrieval gate, and the caller
    must instruct the model to defer rather than answer.
    """
    stmt = select(KnowledgeChunk).where(KnowledgeChunk.org_id == org_id)
    chunks = list(db.execute(stmt).scalars().all())
    if not chunks:
        return []

    by_id = {c.id: c for c in chunks}
    semantic: dict[str, float] = {}

    if query_embedding:
        if IS_POSTGRES and PGVECTOR_AVAILABLE:
            try:
                for cid, sim in _semantic_candidates_postgres(db, org_id, query_embedding, limit * 4):
                    semantic[cid] = sim
            except Exception as e:  # pragma: no cover
                logger.warning("pgvector search failed, using python cosine: %s", e)
        if not semantic:
            for c in chunks:
                if c.embedding:
                    semantic[c.id] = cosine_similarity(query_embedding, list(c.embedding))

    results: list[tuple[KnowledgeChunk, float]] = []
    for c in chunks:
        kw = compute_keyword_overlap_score(query, c.content)
        sem = semantic.get(c.id)
        if sem is not None:
            score = SEMANTIC_WEIGHT * sem + KEYWORD_WEIGHT * kw
        else:
            score = kw
        if score >= min_relevance:
            results.append((c, score))

    results.sort(key=lambda x: x[1], reverse=True)
    logger.debug(
        "knowledge search backend=%s semantic_hits=%d returned=%d",
        vector_backend(), len(semantic), min(len(results), limit),
    )
    return results[:limit]
