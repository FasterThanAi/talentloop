from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_scope
from app.jobs.runner import enqueue_job
from app.jobs.sourcing import get_rizeos_pool_candidates, parse_csv_candidates, parse_zip_resumes
from app.models import User
from app.schemas.candidate import SourcingURLsRequest

router = APIRouter(prefix="/requisitions/{requisition_id}/source", tags=["Sourcing"])


@router.post("/csv", status_code=status.HTTP_202_ACCEPTED)
async def source_from_file(
    requisition_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    contents = await file.read()
    filename = file.filename or ""

    if filename.endswith(".zip"):
        candidates = parse_zip_resumes(contents)
    else:
        text_content = contents.decode("utf-8", errors="ignore")
        candidates = parse_csv_candidates(text_content)

    if not candidates:
        raise HTTPException(status_code=400, detail="No valid candidates found in uploaded file.")

    job_id = await enqueue_job("source_candidates", {
        "org_id": current_user.org_id,
        "requisition_id": requisition_id,
        "candidates": candidates,
        "total": len(candidates)
    })

    return {"job_id": job_id, "status": "queued", "count": len(candidates)}


@router.post("/urls", status_code=status.HTTP_202_ACCEPTED)
async def source_from_urls(
    requisition_id: str,
    req_body: SourcingURLsRequest,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    candidates = []
    for idx, url in enumerate(req_body.urls):
        url_clean = url.strip()
        if not url_clean:
            continue
        # Extract name from url or default
        name_guess = url_clean.rstrip("/").split("/")[-1].replace("-", " ").title()
        candidates.append({
            "full_name": name_guess,
            "email": f"candidate_{idx+1}@profile.dev",
            "phone": None,
            "public_urls": [url_clean],
            "source": "urls"
        })

    if not candidates:
        raise HTTPException(status_code=400, detail="No URLs provided")

    job_id = await enqueue_job("source_candidates", {
        "org_id": current_user.org_id,
        "requisition_id": requisition_id,
        "candidates": candidates,
        "total": len(candidates)
    })

    return {"job_id": job_id, "status": "queued", "count": len(candidates)}


@router.post("/rizeos-pool", status_code=status.HTTP_202_ACCEPTED)
async def source_from_rizeos_pool(
    requisition_id: str,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    candidates = get_rizeos_pool_candidates()
    job_id = await enqueue_job("source_candidates", {
        "org_id": current_user.org_id,
        "requisition_id": requisition_id,
        "candidates": candidates,
        "total": len(candidates)
    })
    return {"job_id": job_id, "status": "queued", "count": len(candidates)}
