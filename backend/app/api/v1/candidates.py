from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.audit import write_audit
from app.core.deps import get_current_user, get_db, require_scope
from app.models import Candidate, CandidateResearch, User
from app.schemas.candidate import CandidateCreate, CandidateOut

router = APIRouter(prefix="/candidates", tags=["Candidates"])


@router.get("", response_model=list[CandidateOut])
def list_candidates(
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    stmt = (
        select(Candidate)
        .options(joinedload(Candidate.research))
        .where(Candidate.org_id == current_user.org_id)
        .order_by(Candidate.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    candidates = db.execute(stmt).scalars().unique().all()
    return [CandidateOut.model_validate(c) for c in candidates]


@router.get("/{id}", response_model=CandidateOut)
def get_candidate(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    stmt = (
        select(Candidate)
        .options(joinedload(Candidate.research))
        .where(Candidate.id == id, Candidate.org_id == current_user.org_id)
    )
    c = db.execute(stmt).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return CandidateOut.model_validate(c)


@router.post("/{id}/do-not-contact", response_model=CandidateOut)
def set_do_not_contact(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    stmt = select(Candidate).where(Candidate.id == id)
    c = db.execute(stmt).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if c.do_not_contact:
        # Attempting to unset or re-toggle is forbidden (irreversible invariant)
        raise HTTPException(
            status_code=409,
            detail={
                "type": "about:blank",
                "title": "Irreversible do-not-contact state",
                "status": 409,
                "detail": "Candidate do_not_contact is permanently active and cannot be unset.",
                "code": "DO_NOT_CONTACT_IRREVERSIBLE"
            }
        )

    c.do_not_contact = True
    c.consent_status = "revoked"

    write_audit(
        db=db,
        org_id=c.org_id,
        actor_id=current_user.id,
        action="do_not_contact_set",
        entity="candidate",
        entity_id=c.id,
        payload={"candidate_email": c.email, "set_by": current_user.email}
    )

    db.commit()
    db.refresh(c)
    return CandidateOut.model_validate(c)


@router.get("/{id}/data-export")
def export_candidate_data(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    stmt = (
        select(Candidate)
        .options(joinedload(Candidate.research), joinedload(Candidate.pipeline_entries))
        .where(Candidate.id == id)
    )
    c = db.execute(stmt).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # If user is candidate, ensure it's their own record
    if current_user.role == "candidate" and current_user.email.lower() != c.email.lower():
        raise HTTPException(status_code=403, detail="Forbidden: You can only export your own data")

    write_audit(
        db=db,
        org_id=c.org_id,
        actor_id=current_user.id,
        action="candidate_data_exported",
        entity="candidate",
        entity_id=c.id,
        payload={"email": c.email}
    )
    db.commit()

    return {
        "candidate": {
            "id": c.id,
            "full_name": c.full_name,
            "email": c.email,
            "phone": c.phone,
            "source": c.source,
            "public_urls": c.public_urls,
            "consent_status": c.consent_status,
            "do_not_contact": c.do_not_contact,
            "created_at": c.created_at.isoformat()
        },
        "research": {
            "summary": c.research.summary if c.research else None,
            "skills": c.research.skills if c.research else [],
            "projects": c.research.projects if c.research else [],
            "evidence_urls": c.research.evidence_urls if c.research else []
        } if c.research else None
    }


@router.delete("/{id}/data", status_code=status.HTTP_200_OK)
def delete_candidate_data(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    stmt = select(Candidate).where(Candidate.id == id, Candidate.org_id == current_user.org_id)
    c = db.execute(stmt).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Write tombstone audit event
    write_audit(
        db=db,
        org_id=c.org_id,
        actor_id=current_user.id,
        action="candidate_data_deleted",
        entity="candidate",
        entity_id=c.id,
        payload={"tombstone_email": c.email, "deleted_by": current_user.email}
    )

    db.delete(c)
    db.commit()
    return {"status": "deleted", "candidate_id": id, "tombstone_created": True}
