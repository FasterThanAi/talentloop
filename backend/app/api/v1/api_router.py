from fastapi import APIRouter

from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.candidates import router as candidates_router
from app.api.v1.credentials import router as credentials_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.outreach import router as outreach_router
from app.api.v1.pipeline import router as pipeline_router
from app.api.v1.replies import router as replies_router
from app.api.v1.requisitions import router as requisitions_router
from app.api.v1.sourcing import router as sourcing_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(requisitions_router)
api_v1_router.include_router(sourcing_router)
api_v1_router.include_router(pipeline_router)
api_v1_router.include_router(outreach_router)
api_v1_router.include_router(replies_router)
api_v1_router.include_router(feedback_router)
api_v1_router.include_router(candidates_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(credentials_router)
api_v1_router.include_router(audit_router)
