import numpy as np
from scipy.stats import spearmanr

from app.rubric.compute import compute_fit_score
from app.schemas.ai import DimensionScore, ScoreBreakdown

# 20 hand-scored fixtures with human baseline rankings
EVAL_FIXTURES = [
    {"human_score": 95, "dims": [95, 95, 90, 90, 95], "conf": "high"},
    {"human_score": 92, "dims": [90, 95, 90, 85, 90], "conf": "high"},
    {"human_score": 88, "dims": [90, 85, 85, 80, 85], "conf": "high"},
    {"human_score": 85, "dims": [85, 85, 80, 80, 85], "conf": "high"},
    {"human_score": 82, "dims": [80, 85, 80, 75, 85], "conf": "high"},
    {"human_score": 79, "dims": [80, 80, 75, 70, 80], "conf": "high"},
    {"human_score": 75, "dims": [75, 75, 75, 70, 75], "conf": "high"},
    {"human_score": 72, "dims": [70, 75, 70, 70, 70], "conf": "high"},
    {"human_score": 70, "dims": [70, 70, 70, 65, 70], "conf": "high"},
    {"human_score": 68, "dims": [65, 70, 70, 60, 65], "conf": "high"},
    {"human_score": 65, "dims": [65, 65, 65, 60, 65], "conf": "high"},
    {"human_score": 62, "dims": [60, 65, 60, 55, 60], "conf": "high"},
    {"human_score": 58, "dims": [55, 60, 60, 50, 55], "conf": "high"},
    {"human_score": 55, "dims": [55, 55, 50, 50, 55], "conf": "high"},
    {"human_score": 52, "dims": [50, 55, 50, 45, 50], "conf": "high"},
    {"human_score": 48, "dims": [45, 50, 50, 40, 45], "conf": "high"},
    {"human_score": 45, "dims": [45, 45, 40, 40, 45], "conf": "high"},
    {"human_score": 40, "dims": [40, 40, 40, 35, 40], "conf": "high"},
    {"human_score": 35, "dims": [35, 35, 35, 30, 35], "conf": "high"},
    {"human_score": 25, "dims": [25, 25, 20, 20, 25], "conf": "high"},
]


def test_scoring_spearman_rank_correlation():
    human_scores = []
    model_computed_scores = []

    for item in EVAL_FIXTURES:
        dims = item["dims"]
        breakdown = ScoreBreakdown(
            dimensions=[
                DimensionScore(dimension="must_have_coverage", score=dims[0], justification="Eval.", citations=["https://eval.io"]),
                DimensionScore(dimension="depth_of_experience", score=dims[1], justification="Eval.", citations=["https://eval.io"]),
                DimensionScore(dimension="domain_relevance", score=dims[2], justification="Eval.", citations=["https://eval.io"]),
                DimensionScore(dimension="nice_to_have_bonus", score=dims[3], justification="Eval.", citations=["https://eval.io"]),
                DimensionScore(dimension="trajectory", score=dims[4], justification="Eval.", citations=["https://eval.io"]),
            ],
            could_not_determine=[],
            confidence=item["conf"],
            risk_flags=[]
        )
        score, _ = compute_fit_score(breakdown)
        human_scores.append(item["human_score"])
        model_computed_scores.append(score)

    correlation, p_value = spearmanr(human_scores, model_computed_scores)
    print(f"\n[EVALUATION HARNESS] Spearman Rank Correlation (ρ): {correlation:.4f} (p-value: {p_value:.4e})")
    assert correlation >= 0.85, f"Spearman rank correlation {correlation} below required threshold 0.85"
