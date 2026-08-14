import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Importing these modules is what REGISTERS their job handlers. Without an explicit import
# here, registration depends on some router happening to import them, which is how
# "score_candidates" ended up unregistered in production. Import them deliberately.
import app.jobs.enrichment  # noqa: F401  (registers enrich_candidates)
import app.jobs.scoring  # noqa: F401  (registers score_candidates)
import app.jobs.sourcing  # noqa: F401  (registers source_candidates)
from app.ai.client import active_providers, ai_is_mocked
from app.api.v1.api_router import api_v1_router
from app.core.config import settings
from app.core.db import check_db_connection, check_pgvector_extension
from app.core.idempotency import IdempotencyMiddleware
from app.core.vector import vector_backend
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

# ORDER MATTERS. Starlette applies middleware in REVERSE order of registration, so the
# LAST one added is the OUTERMOST. CORS must be outermost: if it sits inside another
# middleware and something further in fails, the error response goes back without
# Access-Control-Allow-Origin, and the browser reports a misleading "blocked by CORS
# policy" instead of the actual 500. Register Idempotency first, CORS last.
app.add_middleware(IdempotencyMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch-all so an unexpected failure returns a readable problem-detail body instead of a
    bare 500.

    This also fixes a confusing symptom: an unhandled exception used to escape past the
    CORS middleware, so the browser received a response with no Access-Control-Allow-Origin
    header and reported "blocked by CORS policy" — hiding the real error entirely. Handling
    it here keeps the response inside the CORS layer, so the frontend sees the actual cause.
    """
    logger.exception("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={
            "type": "about:blank",
            "title": "Internal server error",
            "status": 500,
            "detail": str(exc) or "An unexpected error occurred.",
            "code": "INTERNAL_ERROR",
        },
    )


# Mount v1 router at /api/v1
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"product": "TalentLoop", "version": "0.1.0", "docs": "/docs"}
