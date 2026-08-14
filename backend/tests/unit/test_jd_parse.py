"""
Contract test for jd_parse.v1 — the prompt must return something that satisfies IdealProfile.

It runs against the mock provider by default. Running it live spends real daily quota: three
generations per run, out of a free-tier budget of twenty, which is how a routine `pytest`
ended up being the reason a demo had no quota left. Set RUN_LIVE_AI_TESTS=1 deliberately if
you want to verify the prompt against a real model.
"""
import os

import pytest

from app.ai.client import ai_is_mocked
from app.ai.runner import AIValidationError, run_structured
from app.schemas.ai import IdealProfile

RUN_LIVE = os.getenv("RUN_LIVE_AI_TESTS") == "1"

pytestmark = pytest.mark.skipif(
    not ai_is_mocked() and not RUN_LIVE,
    reason=(
        "A live AI provider is configured; this test would spend real quota. "
        "Set RUN_LIVE_AI_TESTS=1 to run it against the real model."
    ),
)

FIXTURE_JDS = [
    """
    Senior Backend Engineer (Python / FastAPI)
    We are seeking a senior backend engineer to architect and own our real-time matching API.
    Requirements:
    - 4+ years of Python with hands-on FastAPI in production.
    - PostgreSQL schema design and query optimization.
    - Strong system architecture skills.
    Bonus if you know pgvector or have Docker experience.
    """,
    """
    Full Stack Developer (FastAPI + React)
    Join our seed-stage startup building AI agents.
    Must have:
    - Proven track record deploying FastAPI backend services.
    - React 18 frontend with state management.
    - Automated testing with pytest.
    """,
    """
    Platform Infrastructure Engineer
    We need an engineer to lead our distributed ingestion engine.
    Must have:
    - Experience maintaining high-throughput async Python queues.
    - Strong database indexing and transaction safety.
    """
]


@pytest.mark.asyncio
async def test_jd_parse_fixtures():
    for jd_text in FIXTURE_JDS:
        profile, ai_res = await run_structured(
            prompt_name="jd_parse.v1",
            variables={"jd_raw": jd_text},
            schema=IdealProfile,
            temperature=0.0
        )
        assert profile.role_title
        assert profile.seniority in ("intern", "junior", "mid", "senior", "lead", "principal")
        assert len(profile.must_have_skills) > 0
        assert profile.domain_context
