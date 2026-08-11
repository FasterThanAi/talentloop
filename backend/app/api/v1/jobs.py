from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models import Job, User
from app.schemas.job import JobOut

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/{id}", response_model=JobOut)
def get_job_status(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    stmt = select(Job).where(Job.id == id, Job.org_id == current_user.org_id)
    job = db.execute(stmt).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut.model_validate(job)
