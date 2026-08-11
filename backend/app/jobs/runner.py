import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import Job

logger = logging.getLogger("talentloop.jobs")

_JOB_HANDLERS: dict[str, Callable[..., Coroutine[Any, Any, None]]] = {}


def register_job_handler(name: str, handler: Callable[..., Coroutine[Any, Any, None]]) -> None:
    _JOB_HANDLERS[name] = handler


def create_job(db: Session, org_id: str, name: str, total: int = 0) -> Job:
    job = Job(
        org_id=org_id,
        name=name,
        status="queued",
        processed=0,
        total=total,
        errors=[]
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_job_progress(
    job_id: str,
    processed_delta: int = 1,
    error_entry: dict[str, Any] | None = None,
    result_ref: str | None = None
) -> None:
    """Updates job progress in its own standalone transaction so crashes don't lose batch progress."""
    db = SessionLocal()
    try:
        stmt = select(Job).where(Job.id == job_id)
        job = db.execute(stmt).scalar_one_or_none()
        if job:
            job.processed += processed_delta
            if error_entry:
                job.errors = list(job.errors) + [error_entry]
            if result_ref:
                job.result_ref = result_ref
            if job.processed >= job.total and job.total > 0:
                job.status = "completed"
            elif job.status == "queued":
                job.status = "processing"
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update job {job_id} progress: {e}")
        db.rollback()
    finally:
        db.close()


def set_job_status(job_id: str, status: str, result_ref: str | None = None) -> None:
    db = SessionLocal()
    try:
        stmt = select(Job).where(Job.id == job_id)
        job = db.execute(stmt).scalar_one_or_none()
        if job:
            job.status = status
            if result_ref:
                job.result_ref = result_ref
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update job {job_id} status to {status}: {e}")
        db.rollback()
    finally:
        db.close()


async def enqueue_job(name: str, payload: dict[str, Any]) -> str:
    handler = _JOB_HANDLERS.get(name)
    if not handler:
        raise ValueError(f"No job handler registered for '{name}'")

    db = SessionLocal()
    try:
        org_id = payload.get("org_id", "default-org")
        total = payload.get("total", 0)
        job = create_job(db, org_id=org_id, name=name, total=total)
        job_id = job.id
    finally:
        db.close()

    # Launch asynchronously
    asyncio.create_task(_run_job_wrapper(handler, job_id, payload))
    return job_id


async def _run_job_wrapper(
    handler: Callable[..., Coroutine[Any, Any, None]],
    job_id: str,
    payload: dict[str, Any]
) -> None:
    set_job_status(job_id, "processing")
    try:
        await handler(job_id, payload)
        set_job_status(job_id, "completed")
    except Exception as e:
        logger.exception(f"Job {job_id} execution failed: {e}")
        update_job_progress(job_id, processed_delta=0, error_entry={"error": str(e), "fatal": True})
        set_job_status(job_id, "failed")
