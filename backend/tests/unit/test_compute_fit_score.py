import pytest

from app.rubric.compute import compute_fit_score
from app.schemas.ai import DimensionScore, IdealProfile, ScoreBreakdown, SkillRequirement


def test_compute_fit_score_determinism():
    breakdown = ScoreBreakdown(
        dimensions=[
            DimensionScore(dimension="must_have_coverage", score=90, justification="All evidenced.", citations=["https://example.com/a"]),
            DimensionScore(dimension="depth_of_experience", score=80, justification="4 years production.", citations=["https://example.com/a"]),
            DimensionScore(dimension="domain_relevance", score=85, justification="High match.", citations=["https://example.com/a"]),
            DimensionScore(dimension="nice_to_have_bonus", score=70, justification="Docker known.", citations=["https://example.com/a"]),
            DimensionScore(dimension="trajectory", score=90, justification="Lead engineer.", citations=["https://example.com/a"]),
        ],
        could_not_determine=[],
        confidence="high",
        risk_flags=[]
    )

    # 90*0.4 + 80*0.25 + 85*0.15 + 70*0.10 + 90*0.10 = 36 + 20 + 12.75 + 7 + 9 = 84.75 -> 85
    score1, reason1 = compute_fit_score(breakdown)
    score2, reason2 = compute_fit_score(breakdown)

    assert score1 == 85
    assert score1 == score2
    assert reason1 == reason2


def test_low_confidence_cap():
    breakdown = ScoreBreakdown(
        dimensions=[
            DimensionScore(dimension="must_have_coverage", score=100, justification="Looks good.", citations=["https://example.com"]),
            DimensionScore(dimension="depth_of_experience", score=100, justification="Looks good.", citations=["https://example.com"]),
            DimensionScore(dimension="domain_relevance", score=100, justification="Looks good.", citations=["https://example.com"]),
            DimensionScore(dimension="nice_to_have_bonus", score=100, justification="Looks good.", citations=["https://example.com"]),
            DimensionScore(dimension="trajectory", score=100, justification="Looks good.", citations=["https://example.com"]),
        ],
        could_not_determine=["Sparse public evidence"],
        confidence="low",
        risk_flags=[]
    )
    score, _ = compute_fit_score(breakdown)
    assert score == 70, f"Expected low confidence cap of 70, got {score}"


def test_missing_must_have_cap():
    ideal = IdealProfile(
        role_title="Backend Engineer",
        seniority="senior",
        must_have_skills=[
            SkillRequirement(skill="FastAPI", why_required="Core framework", evidence_of="Deployed API")
        ],
        nice_to_have_skills=[],
        domain_context="SaaS",
        implicit_signals=[],
        ambiguities=[]
    )

    breakdown = ScoreBreakdown(
        dimensions=[
            DimensionScore(dimension="must_have_coverage", score=40, justification="Missing FastAPI.", citations=["https://example.com"]),
            DimensionScore(dimension="depth_of_experience", score=90, justification="Strong Python.", citations=["https://example.com"]),
            DimensionScore(dimension="domain_relevance", score=90, justification="High relevance.", citations=["https://example.com"]),
            DimensionScore(dimension="nice_to_have_bonus", score=90, justification="Bonus verified.", citations=["https://example.com"]),
            DimensionScore(dimension="trajectory", score=90, justification="Solid lead.", citations=["https://example.com"]),
        ],
        could_not_determine=["FastAPI experience"],
        confidence="high",
        risk_flags=[]
    )
    score, _ = compute_fit_score(breakdown, ideal)
    assert score <= 60, f"Expected missing must-have cap <= 60, got {score}"
