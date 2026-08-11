import pytest

from app.ai.runner import AIValidationError, run_structured
from app.schemas.ai import IdealProfile

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
