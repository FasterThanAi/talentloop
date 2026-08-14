import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.ai.client import active_providers, ai_is_mocked
from app.api.v1.api_router import api_v1_router
from app.core.config import settings
from app.core.db import check_db_connection, check_pgvector_extension
from app.core.idempotency import IdempotencyMiddleware
from app.core.vector import vector_backend

# Importing these modules is what REGISTERS their job handlers. Without an explicit import
# here, registration depends on some router happening to import them, which is how
# "score_candidates" ended up unregistered in production. Import them deliberately.
import app.jobs.enrichment  # noqa: F401  (registers enrich_candidates)
import app.jobs.scoring  # noqa: F401  (registers score_candidates)
import app.jobs.sourcing  # noqa: F401  (registers source_candidates)
from app.jobs.runner import registered_job_handlers, verify_job_handlers

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("talentloop.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logging checks (P0 requirement)
    db_ok = check_db_connection()
    pgvector_ok = check_pgvector_extension()
    gemini_ok = bool(settings.GEMINI_API_KEY)
    gmail_ok = bool(settings.GMAIL_CLIENT_ID and settings.GMAIL_CLIENT_SECRET)

    logger.info("=== TalentLoop System Startup Checks ===")
    logger.info(f"1. Database Reachable:      [{'OK' if db_ok else 'WARN: Unreachable'}]")
    logger.info(f"2. pgvector Extension:      [{'OK' if pgvector_ok else 'WARN: Missing'}]")
    logger.info(f"3. Gemini API Key:          [{'OK' if gemini_ok else 'INFO: unset'}]")
    logger.info(f"3b. AI provider chain:      [{' -> '.join(active_providers()) or 'NONE (mock mode)'}]")
    logger.info(f"4. Gmail OAuth Credentials: [{'OK' if gmail_ok else 'INFO: Mock mode / credentials unset'}]")
    logger.info(f"5. DB dialect:              [{'postgresql' if settings.DATABASE_URL.startswith(('postgresql', 'postgres://')) else 'sqlite (dev fallback)'}]")
    logger.info(f"6. Vector backend:          [{vector_backend()}]")
    missing_handlers = verify_job_handlers()
    logger.info(f"7. Job handlers:            [{'OK: ' + ', '.join(registered_job_handlers()) if not missing_handlers else 'MISSING: ' + ', '.join(missing_handlers)}]")
    logger.info("=========================================")

    if missing_handlers:
        # Loud, because the symptom otherwise is a button that 500s only when pressed.
        logger.error(
            "JOB HANDLERS MISSING: %s — any endpoint enqueueing these will fail at runtime. "
            "Check that the module registering each one is imported in app/main.py.",
            ", ".join(missing_handlers),
        )

    if ai_is_mocked():
        logger.warning("")
        logger.warning("  *********************************************************")
        logger.warning("  *  AI MOCK MODE ACTIVE - NO REAL MODEL CALLS ARE MADE   *")
        logger.warning("  *  Every AI result is canned. DO NOT DEMO IN THIS MODE. *")
        logger.warning("  *  Set GEMINI_API_KEY or GROQ_API_KEY to fix.           *")
        logger.warning("  *********************************************************")
        logger.warning("")
    if settings.DATABASE_URL.startswith("sqlite"):
        logger.warning(
            "SQLite is a local-dev fallback. Set DATABASE_URL to the Supabase Postgres URI "
            "before demoing: pgvector search and append-only audit enforcement require Postgres."
        )

    yield
    logger.info("TalentLoop backend shutting down.")


app = FastAPI(
    title="TalentLoop API",
    description="Agentic hiring assistant with explainable fit scoring and approval-gated outreach.",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Idempotency Middleware for 24h key deduplication
app.add_middleware(IdempotencyMiddleware)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Formats all HTTP errors into the standard problem-detail envelope."""
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    detail_msg = str(exc.detail) if exc.detail else "An error occurred."
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": "about:blank",
            "title": exc.detail if isinstance(exc.detail, str) else "Error",
            "status": exc.status_code,
            "detail": detail_msg,
            "code": f"HTTP_{exc.status_code}"
        }
    )


# Mount v1 router at /api/v1
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"product": "TalentLoop", "version": "0.1.0", "docs": "/docs"}
