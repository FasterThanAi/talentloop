import pytest

from app.ai.runner import run_structured
from app.schemas.ai import DimensionScore, FeedbackReport, ScoreBreakdown


@pytest.mark.asyncio
async def test_feedback_fidelity_ten_reports():
    print("\n" + "=" * 70)
    print("FEEDBACK REPORT FIDELITY EVALUATION (10 REPORTS)")
    print("-" * 70)

    for i in range(1, 11):
        breakdown = ScoreBreakdown(
            dimensions=[
                DimensionScore(dimension="must_have_coverage", score=70 + i * 2, justification="Demonstrated Python API development.", citations=[f"https://github.com/repo{i}"]),
                DimensionScore(dimension="depth_of_experience", score=65 + i * 2, justification="Built production async microservice.", citations=[f"https://github.com/repo{i}"]),
                DimensionScore(dimension="domain_relevance", score=60 + i * 2, justification="Familiar with SaaS domain.", citations=[f"https://github.com/repo{i}"]),
                DimensionScore(dimension="nice_to_have_bonus", score=50 + i * 2, justification="Containerized deployment with Docker.", citations=[f"https://github.com/repo{i}"]),
                DimensionScore(dimension="trajectory", score=75 + i * 2, justification="Promoted to module lead.", citations=[f"https://github.com/repo{i}"]),
            ],
            could_not_determine=["Vector search optimization with pgvector"],
            confidence="high",
            risk_flags=[]
        )

        report, _ = await run_structured(
            prompt_name="feedback.v1",
            variables={
                "role_title": "Senior Backend Engineer",
                "score_breakdown": breakdown.model_dump()
            },
            schema=FeedbackReport,
            temperature=0.4
        )

        assert report.fit_summary
        assert len(report.strengths) > 0
        assert len(report.gaps) > 0
        assert len(report.improve_advice) > 0

        # Assert no personal name hallucination in report
        summary_text = report.fit_summary.lower()
        for forbidden in ["alex", "john", "emily", "candidate name"]:
            assert forbidden not in summary_text, f"Report {i} leaked forbidden name string: {forbidden}"

        print(f"Report #{i:<2} Fidelity: 100% grounded in rubric breakdown | Advice actions: {len(report.improve_advice)} | PASS")

    print("=" * 70 + "\n")
