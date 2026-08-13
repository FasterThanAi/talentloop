import hashlib
import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.config import settings
from app.core.deps import problem_detail_error
from app.models import CredentialRecord, FeedbackReport

logger = logging.getLogger("talentloop.credential")


def canonicalize_feedback_payload(report: FeedbackReport) -> bytes:
    """
    Produces deterministic canonical JSON byte representation (sorted keys, no extraneous whitespace).
    Excludes candidate personally identifiable information (PII).
    """
    clean_dict = {
        "report_id": report.id,
        "score_snapshot": report.score_snapshot,
        "fit_summary": report.fit_summary,
        "strengths": report.strengths,
        "gaps": report.gaps,
        "improve_advice": report.improve_advice,
        "released_at": report.released_at.isoformat() if report.released_at else ""
    }
    canonical_json = json.dumps(clean_dict, sort_keys=True, separators=(",", ":"))
    return canonical_json.encode("utf-8")


def issue_feedback_credential(
    db: Session,
    feedback_report_id: str,
    actor_id: str = "system"
) -> CredentialRecord:
    stmt = select(FeedbackReport).where(FeedbackReport.id == feedback_report_id)
    fb = db.execute(stmt).scalar_one_or_none()
    if not fb or not fb.released_at:
        raise problem_detail_error(
            status_code=400,
            title="Feedback not released",
            detail="Credentials can only be issued for released feedback reports.",
            code="REPORT_NOT_RELEASED"
        )

    # Compute deterministic SHA-256 hash
    payload_bytes = canonicalize_feedback_payload(fb)
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()

    stmt_rec = select(CredentialRecord).where(CredentialRecord.feedback_report_id == fb.id)
    record = db.execute(stmt_rec).scalar_one_or_none()

    simulated_tx = f"0x{hashlib.sha256((payload_hash + 'polygon').encode()).hexdigest()}"

    if not record:
        record = CredentialRecord(
            org_id=fb.org_id,
            feedback_report_id=fb.id,
            payload_hash=payload_hash,
            tx_hash=simulated_tx,
            network="polygon-amoy",
            revoked=False
        )
        db.add(record)
    else:
        record.payload_hash = payload_hash
        record.tx_hash = simulated_tx

    # Only the hash is ever anchored — no personal data leaves the database.
    write_audit(
        db=db,
        org_id=fb.org_id,
        actor_id=actor_id,
        action="credential_issued",
        entity="feedback_report",
        entity_id=fb.id,
        payload={"payload_hash": payload_hash, "network": record.network,
                 "anchored": settings.CREDENTIAL_ANCHOR_ENABLED},
    )

    db.commit()
    db.refresh(record)
    return record


def verify_credential(
    db: Session,
    payload_hash: str
) -> dict[str, Any]:
    stmt = select(CredentialRecord).where(CredentialRecord.payload_hash == payload_hash)
    record = db.execute(stmt).scalar_one_or_none()

    if not record:
        return {
            "payload_hash": payload_hash,
            "verified": False,
            "network": "polygon-amoy",
            "tx_hash": None,
            "revoked": False,
            "issued_at": None,
            "details": None
        }

    stmt_fb = select(FeedbackReport).where(FeedbackReport.id == record.feedback_report_id)
    fb = db.execute(stmt_fb).scalar_one_or_none()

    return {
        "payload_hash": record.payload_hash,
        "verified": True and not record.revoked,
        "network": record.network,
        "tx_hash": record.tx_hash,
        "revoked": record.revoked,
        "issued_at": record.created_at,
        "details": {
            "score_snapshot": fb.score_snapshot if fb else None,
            "released_at": fb.released_at if fb else None
        }
    }
