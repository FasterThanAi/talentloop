import csv
import io
import logging
import zipfile
from typing import Any, Dict, List, Tuple

import docx
import pypdf
from sqlalchemy import select

from app.core.audit import write_audit
from app.core.db import SessionLocal
from app.jobs.enrichment import handle_enrichment_job
from app.jobs.runner import enqueue_job, register_job_handler, update_job_progress
from app.models import Candidate, PipelineEntry

logger = logging.getLogger("talentloop.sourcing")


def parse_csv_candidates(csv_content: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(csv_content))
    candidates = []
    for row in reader:
        # Normalize column keys
        normalized = {k.strip().lower(): v.strip() for k, v in row.items() if k and v}
        name = normalized.get("name") or normalized.get("full_name") or normalized.get("candidate_name") or "Candidate"
        email = normalized.get("email") or normalized.get("email_address")
        phone = normalized.get("phone") or normalized.get("phone_number")
        
        urls_field = normalized.get("urls") or normalized.get("public_urls") or normalized.get("github") or normalized.get("portfolio")
        urls = [u.strip() for u in urls_field.split(";") if u.strip()] if urls_field else []

        if email:
            candidates.append({
                "full_name": name,
                "email": email.lower(),
                "phone": phone,
                "public_urls": urls,
                "source": "csv"
            })
    return candidates


def parse_zip_resumes(zip_bytes: bytes) -> list[dict[str, Any]]:
    candidates = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for filename in z.namelist():
            if filename.startswith("__MACOSX") or filename.endswith("/"):
                continue

            file_content = z.read(filename)
            extracted_text = ""

            if filename.lower().endswith(".pdf"):
                try:
                    pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
                    for page in pdf_reader.pages:
                        extracted_text += (page.extract_text() or "") + "\n"
                except Exception as e:
                    logger.warning(f"Failed to extract PDF {filename}: {e}")

            elif filename.lower().endswith(".docx"):
                try:
                    doc = docx.Document(io.BytesIO(file_content))
                    extracted_text = "\n".join(p.text for p in doc.paragraphs)
                except Exception as e:
                    logger.warning(f"Failed to extract DOCX {filename}: {e}")

            if extracted_text:
                # Infer name from filename
                base_name = filename.split("/")[-1].rsplit(".", 1)[0].replace("_", " ").replace("-", " ")
                email_match = next((word for word in extracted_text.split() if "@" in word and "." in word), None)
                email = email_match.strip("<>()[]:,") if email_match else f"{base_name.lower().replace(' ', '.')}@example.com"

                candidates.append({
                    "full_name": base_name.title(),
                    "email": email.lower(),
                    "phone": None,
                    "public_urls": [f"https://github.com/{base_name.lower().replace(' ', '')}"],
                    "source": "resume_zip"
                })
    return candidates


def get_rizeos_pool_candidates() -> list[dict[str, Any]]:
    """Fixture shape for RizeOS talent pool integration."""
    return [
        {
            "full_name": "Marcus Vance",
            "email": "marcus.vance@rizeos-pool.dev",
            "phone": "+1 415-555-0199",
            "public_urls": ["https://github.com/marcusvance", "https://marcusvance.io"],
            "source": "rizeos_pool"
        },
        {
            "full_name": "Sophia Zhang",
            "email": "sophia.zhang@rizeos-pool.dev",
            "phone": "+1 415-555-0188",
            "public_urls": ["https://github.com/sophiazhang-ai", "https://sophiazhang.me"],
            "source": "rizeos_pool"
        },
        {
            "full_name": "Devin O'Connor",
            "email": "devin.oconnor@rizeos-pool.dev",
            "phone": "+1 415-555-0177",
            "public_urls": ["https://github.com/devin-oconnor"],
            "source": "rizeos_pool"
        }
    ]


async def handle_sourcing_job(job_id: str, payload: dict[str, Any]) -> None:
    org_id = payload["org_id"]
    requisition_id = payload["requisition_id"]
    raw_candidates: list[dict[str, Any]] = payload.get("candidates", [])

    db = SessionLocal()
    newly_created_ids = []
    try:
        for item in raw_candidates:
            email = item["email"].strip().lower()
            try:
                # Check for duplicate candidate within organization
                stmt = select(Candidate).where(
                    Candidate.org_id == org_id,
                    Candidate.email == email
                )
                existing = db.execute(stmt).scalar_one_or_none()

                if not existing:
                    candidate = Candidate(
                        org_id=org_id,
                        full_name=item["full_name"],
                        email=email,
                        phone=item.get("phone"),
                        source=item.get("source", "csv"),
                        public_urls=item.get("public_urls", []),
                        consent_status="granted"
                    )
                    db.add(candidate)
                    db.flush()
                else:
                    candidate = existing

                # Check for existing pipeline entry
                stmt_pe = select(PipelineEntry).where(
                    PipelineEntry.requisition_id == requisition_id,
                    PipelineEntry.candidate_id == candidate.id
                )
                existing_pe = db.execute(stmt_pe).scalar_one_or_none()

                if not existing_pe:
                    pe = PipelineEntry(
                        org_id=org_id,
                        requisition_id=requisition_id,
                        candidate_id=candidate.id,
                        stage="sourced"
                    )
                    db.add(pe)
                    db.commit()
                    newly_created_ids.append(candidate.id)
                else:
                    # Duplicate entry in requisition: skip and note informational error
                    update_job_progress(
                        job_id,
                        processed_delta=1,
                        error_entry={"email": email, "info": "Candidate already present in requisition pipeline"}
                    )
                    continue

                update_job_progress(job_id, processed_delta=1)
            except Exception as item_err:
                db.rollback()
                logger.error(f"Failed to process candidate {email}: {item_err}")
                update_job_progress(job_id, processed_delta=1, error_entry={"email": email, "error": str(item_err)})

        # One audit row per sourcing run, inside the job's own session.
        write_audit(
            db=db,
            org_id=org_id,
            actor_id=payload.get("actor_id", "system"),
            action="candidates_sourced",
            entity="requisition",
            entity_id=requisition_id,
            payload={
                "source": payload.get("source", "csv"),
                "submitted": len(raw_candidates),
                "created": len(newly_created_ids),
            },
        )
        db.commit()
    finally:
        db.close()

    # Enqueue enrichment for newly added candidates with URLs
    if newly_created_ids:
        await enqueue_job("enrich_candidates", {
            "org_id": org_id,
            "candidate_ids": newly_created_ids,
            "total": len(newly_created_ids)
        })


register_job_handler("source_candidates", handle_sourcing_job)
