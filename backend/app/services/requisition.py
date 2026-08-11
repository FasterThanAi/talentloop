import logging
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.runner import AIValidationError, run_structured
from app.core.audit import write_audit
from app.core.deps import problem_detail_error
from app.models import Requisition, User
from app.schemas.ai import IdealProfile
from app.schemas.requisition import RequisitionCreate, RequisitionUpdate

logger = logging.getLogger("talentloop.requisition")


async def parse_and_update_requisition(
    db: Session,
    requisition_id: str,
    actor_id: str
) -> tuple[Requisition, IdealProfile, dict[str, Any]]:
    stmt = select(Requisition).where(Requisition.id == requisition_id)
    req = db.execute(stmt).scalar_one_or_none()
    if not req:
        raise problem_detail_error(
            status_code=404,
            title="Requisition not found",
            detail=f"Requisition {requisition_id} does not exist.",
            code="REQUISITION_NOT_FOUND"
        )

    try:
        ideal_profile, ai_result = await run_structured(
            prompt_name="jd_parse.v1",
            variables={"jd_raw": req.jd_raw},
            schema=IdealProfile,
            temperature=0.0
        )

        req.parsed_profile = ideal_profile.model_dump()
        req.title = ideal_profile.role_title
        req.seniority = ideal_profile.seniority
        req.location = ideal_profile.location_constraint or req.location
        req.status = "parsed"

        write_audit(
            db=db,
            org_id=req.org_id,
            actor_id=actor_id,
            action="requisition_parsed",
            entity="requisition",
            entity_id=req.id,
            payload={"role_title": req.title, "seniority": req.seniority}
        )

        db.commit()
        db.refresh(req)

        ai_meta = {
            "model": ai_result.model,
            "prompt": f"{ai_result.prompt_name}.{ai_result.prompt_version}",
            "input_tokens": ai_result.input_tokens,
            "output_tokens": ai_result.output_tokens,
            "latency_ms": ai_result.latency_ms
        }
        return req, ideal_profile, ai_meta

    except AIValidationError as e:
        req.status = "parse_failed"
        db.commit()
        raise problem_detail_error(
            status_code=422,
            title="Requisition parse failed",
            detail=f"Job description could not be structured: {e}",
            code="REQUISITION_PARSE_FAILED"
        ) from e


async def parse_requisition_jd(
    db: Session,
    requisition_id: str,
    user: User
) -> IdealProfile:
    _, profile, _ = await parse_and_update_requisition(
        db=db,
        requisition_id=requisition_id,
        actor_id=user.id
    )
    return profile


def update_requisition_profile(
    db: Session,
    requisition_id: str,
    user: User,
    data: RequisitionUpdate
) -> Requisition:
    stmt = select(Requisition).where(Requisition.id == requisition_id, Requisition.org_id == user.org_id)
    req = db.execute(stmt).scalar_one_or_none()
    if not req:
        raise problem_detail_error(
            status_code=404,
            title="Requisition not found",
            detail=f"Requisition {requisition_id} does not exist.",
            code="REQUISITION_NOT_FOUND"
        )

    if data.title is not None:
        req.title = data.title
    if data.seniority is not None:
        req.seniority = data.seniority
    if data.location is not None:
        req.location = data.location
    if data.parsed_profile is not None:
        req.parsed_profile = data.parsed_profile

    write_audit(
        db=db,
        org_id=user.org_id,
        actor_id=user.id,
        action="requisition_updated",
        entity="requisition",
        entity_id=req.id,
        payload={"title": req.title}
    )

    db.commit()
    db.refresh(req)
    return req
