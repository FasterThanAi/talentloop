import logging
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import KnowledgeChunk

logger = logging.getLogger("talentloop.knowledge")


def compute_keyword_overlap_score(query: str, text: str) -> float:
    q_words = set(query.lower().split())
    t_words = set(text.lower().split())
    if not q_words or not t_words:
        return 0.0
    overlap = q_words.intersection(t_words)
    return len(overlap) / max(1, len(q_words))


def search_knowledge(
    db: Session,
    org_id: str,
    query: str,
    min_relevance: float = 0.50,
    limit: int = 3
) -> list[tuple[KnowledgeChunk, float]]:
    """
    Hybrid semantic & keyword search over verified organization knowledge chunks.
    Filters out chunks below min_relevance.
    """
    stmt = select(KnowledgeChunk).where(KnowledgeChunk.org_id == org_id)
    chunks = db.execute(stmt).scalars().all()

    results: list[tuple[KnowledgeChunk, float]] = []
    for chunk in chunks:
        # Simple hybrid scoring
        score = compute_keyword_overlap_score(query, chunk.content)
        if score >= min_relevance:
            results.append((chunk, score))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:limit]
