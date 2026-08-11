from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.audit import write_audit
from app.core.deps import get_current_user, get_db, require_scope
from app.models import Candidate, CandidateResearch, User
from app.schemas.candidate import CandidateCreate, CandidateDeleteResponse, CandidateExportOut, CandidateOut

router = APIRouter(prefix="/candidates", tags=["Candidates"])


@router.get("", response_model=List[CandidateOut])
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
        raise HTTPException(
            status_code=404,
            detail={
                "type": "about:blank",
                "title": "Candidate not found",
                "status": 404,
                "detail": f"Candidate with id {id} was not found.",
                "code": "CANDIDATE_NOT_FOUND"
            }
        )
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
        raise HTTPException(
            status_code=404,
            detail={
                "type": "about:blank",
                "title": "Candidate not found",
                "status": 404,
                "detail": f"Candidate with id {id} was not found.",
                "code": "CANDIDATE_NOT_FOUND"
            }
        )

    if c.do_not_contact:
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


@router.get("/{id}/data-export", response_model=CandidateExportOut)
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

    research_dict = None
    if c.research:
        research_dict = {
            "summary": c.research.summary,
            "skills": c.research.skills,
            "projects": c.research.projects,
            "evidence_urls": c.research.evidence_urls
        }

    return CandidateExportOut(
        candidate=CandidateOut.model_validate(c),
        research=research_dict
    )


@router.delete("/{id}/data", response_model=CandidateDeleteResponse, status_code=status.HTTP_200_OK)
def delete_candidate_data(
    id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    stmt = select(Candidate).where(Candidate.id == id, Candidate.org_id == current_user.org_id)
    c = db.execute(stmt).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")

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
    return CandidateDeleteResponse(candidate_id=id, tombstone_created=True)
