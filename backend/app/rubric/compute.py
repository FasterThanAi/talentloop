from typing import List, Optional, Tuple

from app.rubric.dimensions import DIMENSION_MAP, RUBRIC_V1
from app.schemas.ai import IdealProfile, ScoreBreakdown


def compute_fit_score(
    breakdown: ScoreBreakdown,
    ideal_profile: IdealProfile | None = None
) -> tuple[int, str]:
    """
    Deterministic Python scoring engine.
    Invariant #1: The model NEVER produces the final score.
    Computes weighted sum of individual dimension scores, applies strict confidence
    and missing must-have caps, and generates a factual 1-line reason summary.
    """
    raw_weighted_score = 0.0
    dim_scores = {}

    for d in breakdown.dimensions:
        if d.dimension in DIMENSION_MAP:
            weight = DIMENSION_MAP[d.dimension].weight
            raw_weighted_score += d.score * weight
            dim_scores[d.dimension] = d

    final_score = int(round(raw_weighted_score))
    final_score = max(0, min(100, final_score))

    # Rule: Low confidence caps the score at 70
    if breakdown.confidence == "low":
        final_score = min(final_score, 70)

    # Rule: If could_not_determine covers a must-have, cap at 60
    has_missing_must_have = False
    if ideal_profile and ideal_profile.must_have_skills:
        for must_have in ideal_profile.must_have_skills:
            for undetermined in breakdown.could_not_determine:
                if must_have.skill.lower() in undetermined.lower():
                    has_missing_must_have = True
                    break
    elif breakdown.could_not_determine:
        # Check if must_have_coverage dimension scored low or mentioned undetermined must-haves
        must_have_dim = dim_scores.get("must_have_coverage")
        if must_have_dim and must_have_dim.score < 50:
            has_missing_must_have = True

    if has_missing_must_have:
        final_score = min(final_score, 60)

    # Assemble 1-line summary reason:
    # Sort dimensions by score descending
    sorted_dims = sorted(breakdown.dimensions, key=lambda x: x.score, reverse=True)
    top_two = sorted_dims[:2]
    lowest_one = sorted_dims[-1] if len(sorted_dims) > 2 else None

    reasons = [f"Strong {d.dimension.replace('_', ' ')} ({d.score}/100): {d.justification.rstrip('.')}" for d in top_two]
    if lowest_one and lowest_one.score < 70:
        reasons.append(f"Gaps in {lowest_one.dimension.replace('_', ' ')} ({lowest_one.score}/100): {lowest_one.justification.rstrip('.')}")

    reason_summary = "; ".join(reasons) + "."

    return final_score, reason_summary
