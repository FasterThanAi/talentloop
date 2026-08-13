"""
Company knowledge — the corpus that grounds candidate-facing answers.

This is the retrieval side of the retrieval gate: if nothing here clears the relevance
threshold, respond.v1 is instructed to defer rather than answer. Keeping it thin and
explicit matters, because an empty or stale corpus is what turns a grounded assistant
into a guessing one.
"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.config import settings
from app.core.deps import get_db, require_scope
from app.core.vector import vector_backend
from app.models import KnowledgeChunk, User
from app.schemas.knowledge import KnowledgeChunkCreate, KnowledgeChunkOut
from app.services.knowledge import embed_missing_chunks, embed_text, search_knowledge

router = APIRouter(prefix="/knowledge", tags=["Knowledge"])


@router.get("", response_model=list[KnowledgeChunkOut])
def list_knowledge(
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db),
):
    stmt = (
        select(KnowledgeChunk)
        .where(KnowledgeChunk.org_id == current_user.org_id)
        .order_by(KnowledgeChunk.created_at.desc())
    )
    return [KnowledgeChunkOut.model_validate(c) for c in db.execute(stmt).scalars().all()]


@router.post("", response_model=KnowledgeChunkOut, status_code=status.HTTP_201_CREATED)
async def create_knowledge(
    body: KnowledgeChunkCreate,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db),
):
    """Add a verified company fact. Embedded on write when a model is available."""
    chunk = KnowledgeChunk(
        org_id=current_user.org_id,
        source_type=body.source_type,
        content=body.content,
        document_id=body.document_id,
    )
    chunk.embedding = await embed_text(body.content)
    db.add(chunk)

    write_audit(
        db=db,
        org_id=current_user.org_id,
        actor_id=current_user.id,
        action="knowledge_added",
        entity="knowledge_chunk",
        entity_id=chunk.id,
        payload={"source_type": body.source_type, "embedded": chunk.embedding is not None},
    )
    db.commit()
    db.refresh(chunk)
    return KnowledgeChunkOut.model_validate(chunk)


@router.get("/search")
async def search(
    q: str = Query(..., min_length=2),
    min_relevance: float | None = Query(None),
    limit: int = Query(3, le=20),
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db),
):
    """
    Hybrid semantic + keyword search. `gate_open` is the important field: false means the
    retrieval gate would close and the model must defer instead of answering.
    """
    threshold = min_relevance if min_relevance is not None else settings.RESPONSE_MIN_RELEVANCE
    query_vec = await embed_text(q)
    results = search_knowledge(
        db=db,
        org_id=current_user.org_id,
        query=q,
        min_relevance=threshold,
        limit=limit,
        query_embedding=query_vec,
    )
    return {
        "backend": vector_backend(),
        "semantic": query_vec is not None,
        "min_relevance": threshold,
        "gate_open": bool(results),
        "results": [
            {"id": c.id, "score": round(s, 4), "source_type": c.source_type, "content": c.content}
            for c, s in results
        ],
    }


@router.post("/embed-missing")
async def embed_missing(
    limit: int = Query(200, le=1000),
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db),
):
    """Backfill embeddings for chunks that have none. Commits per item, so it is resumable."""
    embedded = await embed_missing_chunks(db=db, org_id=current_user.org_id, limit=limit)
    write_audit(
        db=db,
        org_id=current_user.org_id,
        actor_id=current_user.id,
        action="knowledge_embedded",
        entity="organization",
        entity_id=current_user.org_id,
        payload={"embedded": embedded, "backend": vector_backend()},
    )
    db.commit()
    return {"embedded": embedded, "backend": vector_backend()}
