import pytest
from sqlalchemy import select

from app.core.db import Base, SessionLocal, engine
from app.models import (
    Candidate,
    CandidateResearch,
    FeedbackReport,
    Organization,
    OutreachMessage,
    PipelineEntry,
    Requisition,
    User,
)
from app.seed.demo import purge_placeholders, seed_showcase_data


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield


def test_showcase_seeder_idempotency_and_scores():
    db = SessionLocal()

    # 1. Run showcase seeder first time
    res1 = seed_showcase_data(db=db)
    assert res1["candidates_seeded"] == 6

    # Verify 6 candidates exist and fit scores are valid
    stmt_pe = select(PipelineEntry).where(PipelineEntry.requisition_id == res1["requisition_id"])
    entries = db.execute(stmt_pe).scalars().all()
    assert len(entries) == 6

    for pe in entries:
        # Assert no pipeline entry has null or zero fit_score
        assert pe.fit_score is not None
        assert pe.fit_score > 0
        assert pe.fit_score >= 50
        assert pe.score_breakdown is not None
        assert "dimensions" in pe.score_breakdown
        assert len(pe.score_breakdown["dimensions"]) == 5
        for dim in pe.score_breakdown["dimensions"]:
            assert dim["score"] > 0
            assert len(dim["citations"]) > 0

    # Verify requisition status and profile
    stmt_req = select(Requisition).where(Requisition.id == res1["requisition_id"])
    req = db.execute(stmt_req).scalar_one()
    assert req.status == "parsed"
    assert req.parsed_profile is not None
    assert req.parsed_profile["role_title"] == "Senior Backend Engineer (Python / FastAPI)"

    # Verify outreach messages
    stmt_out = select(OutreachMessage).where(OutreachMessage.org_id == res1["organization_id"])
    outreaches = db.execute(stmt_out).scalars().all()
    assert len(outreaches) == 2
    sent_outreach = [o for o in outreaches if o.status == "sent"]
    draft_outreach = [o for o in outreaches if o.status == "draft"]
    assert len(sent_outreach) == 1
    assert len(draft_outreach) == 1
    assert sent_outreach[0].approved_by is not None
    assert sent_outreach[0].sent_at is not None

    # Verify feedback report
    stmt_fb = select(FeedbackReport).where(FeedbackReport.org_id == res1["organization_id"])
    feedback_reports = db.execute(stmt_fb).scalars().all()
    assert len(feedback_reports) == 1
    assert feedback_reports[0].released_at is not None
    assert feedback_reports[0].score_snapshot == 91

    # Record row counts after run 1
    cands_count_1 = len(db.execute(select(Candidate)).scalars().all())
    pes_count_1 = len(db.execute(select(PipelineEntry)).scalars().all())
    res_count_1 = len(db.execute(select(CandidateResearch)).scalars().all())
    out_count_1 = len(db.execute(select(OutreachMessage)).scalars().all())
    fb_count_1 = len(db.execute(select(FeedbackReport)).scalars().all())
    user_count_1 = len(db.execute(select(User)).scalars().all())

    # 2. Run showcase seeder second time (Idempotence test)
    res2 = seed_showcase_data(db=db)
    assert res2["organization_id"] == res1["organization_id"]
    assert res2["requisition_id"] == res1["requisition_id"]

    # Verify exact same row counts
    cands_count_2 = len(db.execute(select(Candidate)).scalars().all())
    pes_count_2 = len(db.execute(select(PipelineEntry)).scalars().all())
    res_count_2 = len(db.execute(select(CandidateResearch)).scalars().all())
    out_count_2 = len(db.execute(select(OutreachMessage)).scalars().all())
    fb_count_2 = len(db.execute(select(FeedbackReport)).scalars().all())
    user_count_2 = len(db.execute(select(User)).scalars().all())

    assert cands_count_2 == cands_count_1
    assert pes_count_2 == pes_count_1
    assert res_count_2 == res_count_1
    assert out_count_2 == out_count_1
    assert fb_count_2 == fb_count_1
    assert user_count_2 == user_count_1

    db.close()


def test_purge_placeholders_dry_run_and_confirm():
    db = SessionLocal()

    # Create dummy placeholder candidate
    stmt_org = select(Organization).limit(1)
    org = db.execute(stmt_org).scalar_one_or_none()
    if not org:
        org = Organization(name="Test Purge Org", plan="enterprise")
        db.add(org)
        db.flush()

    dummy_cand = Candidate(
        org_id=org.id,
        full_name="Junk Placeholder",
        email="junk_123@sourced.talentloop.local",
        source="csv",
        consent_status="granted"
    )
    db.add(dummy_cand)
    db.flush()

    dummy_research = CandidateResearch(
        org_id=org.id,
        candidate_id=dummy_cand.id,
        summary="Junk summary"
    )
    db.add(dummy_research)
    db.commit()

    # 1. Dry run
    dry_counts = purge_placeholders(confirm=False, db=db)
    assert dry_counts["candidates"] >= 1
    assert dry_counts["research"] >= 1

    # Candidate should still exist
    stmt_check = select(Candidate).where(Candidate.id == dummy_cand.id)
    assert db.execute(stmt_check).scalar_one_or_none() is not None

    # 2. Confirmed purge
    confirmed_counts = purge_placeholders(confirm=True, db=db)
    assert confirmed_counts["candidates"] >= 1

    # Candidate should be deleted
    assert db.execute(stmt_check).scalar_one_or_none() is None

    db.close()
