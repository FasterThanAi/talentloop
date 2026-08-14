import hashlib
import re
import urllib.parse

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_scope
from app.jobs.runner import enqueue_job
from app.jobs.sourcing import get_rizeos_pool_candidates, parse_csv_candidates, parse_zip_resumes
from app.models import User
from app.schemas.candidate import SourcingURLsRequest
from app.schemas.common import JobResponse


def placeholder_email_for_url(url: str) -> str:
    """
    Stable, URL-derived placeholder address for a sourced profile.

    This used to be positional — candidate_1@profile.dev, candidate_2@… — which meant the
    FIRST url of every ingestion produced the SAME address as the first url of every
    previous ingestion. Sourcing dedupes on (org_id, email), so every profile after the
    very first was silently skipped as "already present in requisition pipeline" and never
    appeared in the pipeline.

    Deriving the address from the URL keeps re-ingesting the same profile correctly
    idempotent, while letting genuinely different profiles through. The short hash
    guarantees uniqueness when two different URLs share a slug (e.g. two sites with the
    same username).
    """
    parsed = urllib.parse.urlparse(url)
    host = (parsed.netloc or "unknown").split(":")[0].removeprefix("www.")
    site = re.sub(r"[^a-z0-9]", "", host.split(".")[0].lower()) or "web"
    slug = re.sub(r"[^a-z0-9._-]", "", parsed.path.strip("/").replace("/", "-").lower())[:40] or "profile"
    digest = hashlib.sha1(url.strip().rstrip("/").lower().encode()).hexdigest()[:8]
    return f"{slug}.{site}.{digest}@sourced.talentloop.local"


router = APIRouter(prefix="/requisitions/{requisition_id}/source", tags=["Sourcing"])


@router.post("/csv", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
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
        raise HTTPException(
            status_code=400,
            detail={
                "type": "about:blank",
                "title": "Invalid file content",
                "status": 400,
                "detail": "No valid candidates found in uploaded file.",
                "code": "EMPTY_CANDIDATE_FILE"
            }
        )

    job_id = await enqueue_job("source_candidates", {
        "org_id": current_user.org_id,
        "requisition_id": requisition_id,
        "candidates": candidates,
        "total": len(candidates)
    })

    return JobResponse(job_id=job_id, status="queued", count=len(candidates))


@router.post("/urls", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def source_from_urls(
    requisition_id: str,
    req_body: SourcingURLsRequest,
    current_user: User = Depends(require_scope("recruiter")),
    db: Session = Depends(get_db)
):
    candidates = []
    for url in req_body.urls:
        url_clean = url.strip()
        if not url_clean:
            continue
        name_guess = url_clean.rstrip("/").split("/")[-1].replace("-", " ").title()
        candidates.append({
            "full_name": name_guess,
            "email": placeholder_email_for_url(url_clean),
            "phone": None,
            "public_urls": [url_clean],
            "source": "urls"
        })

    if not candidates:
        raise HTTPException(
            status_code=400,
            detail={
                "type": "about:blank",
                "title": "Missing URLs",
                "status": 400,
                "detail": "No URLs provided for candidate sourcing.",
                "code": "MISSING_SOURCING_URLS"
            }
        )

    job_id = await enqueue_job("source_candidates", {
        "org_id": current_user.org_id,
        "requisition_id": requisition_id,
        "candidates": candidates,
        "total": len(candidates)
    })

    return JobResponse(job_id=job_id, status="queued", count=len(candidates))


@router.post("/rizeos-pool", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
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
    return JobResponse(job_id=job_id, status="queued", count=len(candidates))
