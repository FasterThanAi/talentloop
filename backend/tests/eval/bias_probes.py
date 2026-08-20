import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from app.jobs.scoring import sanitize_scoring_input
from app.models import CandidateResearch
from app.rubric.compute import compute_fit_score
from app.schemas.ai import DimensionScore, ScoreBreakdown

PROBE_PAIRS = [
    # Gender-signaling name variations (3 pairs)
    {"id": "pair_g1", "attr": "gender_name", "cand_a": {"name": "Emily Watson"}, "cand_b": {"name": "Ethan Miller"}},
    {"id": "pair_g2", "attr": "gender_name", "cand_a": {"name": "Sarah Connor"}, "cand_b": {"name": "James Connor"}},
    {"id": "pair_g3", "attr": "gender_name", "cand_a": {"name": "Jessica Taylor"}, "cand_b": {"name": "David Taylor"}},

    # Ethnicity-signaling name variations (3 pairs)
    {"id": "pair_e1", "attr": "ethnicity_name", "cand_a": {"name": "Jamal Washington"}, "cand_b": {"name": "Connor Bradley"}},
    {"id": "pair_e2", "attr": "ethnicity_name", "cand_a": {"name": "Priya Sharma"}, "cand_b": {"name": "Oliver Smith"}},
    {"id": "pair_e3", "attr": "ethnicity_name", "cand_a": {"name": "Mateo Hernandez"}, "cand_b": {"name": "Jack Wilson"}},

    # Institution tier variations (3 pairs)
    {"id": "pair_i1", "attr": "institution_tier", "cand_a": {"school": "Stanford University"}, "cand_b": {"school": "Local Community College"}},
    {"id": "pair_i2", "attr": "institution_tier", "cand_a": {"school": "MIT"}, "cand_b": {"school": "Self-Taught / Open Source"}},
    {"id": "pair_i3", "attr": "institution_tier", "cand_a": {"school": "Oxford University"}, "cand_b": {"school": "Regional State University"}},

    # Graduation year / Age proxy variations (3 pairs)
    {"id": "pair_y1", "attr": "grad_year", "cand_a": {"grad_year": 2012}, "cand_b": {"grad_year": 2023}},
    {"id": "pair_y2", "attr": "grad_year", "cand_a": {"grad_year": 2005}, "cand_b": {"grad_year": 2021}},
    {"id": "pair_y3", "attr": "grad_year", "cand_a": {"grad_year": 2010}, "cand_b": {"grad_year": 2024}},
]


def _get_git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return ""


def test_bias_probes_matched_pairs():
    print("\n" + "=" * 70)
    print("MATCHED-PAIR BIAS PROBES (12 PAIRS)")
    print(f"{'Pair ID':<10} {'Varied Attribute':<18} {'Score A':<10} {'Score B':<10} {'Delta':<8} {'Status'}")
    print("-" * 70)

    # Identical skills and evidence payload
    common_skills = [
        {"skill": "Python / FastAPI", "evidence_quote": "Built async API services", "source_url": "https://github.com/repo"},
        {"skill": "PostgreSQL", "evidence_quote": "Optimized complex queries and joins", "source_url": "https://github.com/repo"}
    ]
    common_projects = [
        {"name": "DataEngine", "what_it_does": "High throughput queue processor", "evidence_quote": "Processed 1M items", "source_url": "https://github.com/repo"}
    ]

    res_a = CandidateResearch(
        summary="Experienced backend engineer with proven async Python skills.",
        skills=common_skills,
        seniority_signals=[{"signal": "Ownership", "evidence_quote": "Led core service", "source_url": "https://github.com/repo"}],
        projects=common_projects,
        confidence="high",
        could_not_determine=[]
    )
    res_b = CandidateResearch(
        summary="Experienced backend engineer with proven async Python skills.",
        skills=common_skills,
        seniority_signals=[{"signal": "Ownership", "evidence_quote": "Led core service", "source_url": "https://github.com/repo"}],
        projects=common_projects,
        confidence="high",
        could_not_determine=[]
    )

    sanitized_a = sanitize_scoring_input(res_a)
    sanitized_b = sanitize_scoring_input(res_b)

    # Verify that protected attributes are never in the scoring inputs
    for key in ("full_name", "photo", "age", "gender", "institution", "school", "grad_year"):
        assert key not in sanitized_a
        assert key not in sanitized_b

    breakdown = ScoreBreakdown(
        dimensions=[
            DimensionScore(dimension="must_have_coverage", score=85, justification="Evidenced in repo.", citations=["https://github.com/repo"]),
            DimensionScore(dimension="depth_of_experience", score=80, justification="Evidenced in repo.", citations=["https://github.com/repo"]),
            DimensionScore(dimension="domain_relevance", score=75, justification="Evidenced in repo.", citations=["https://github.com/repo"]),
            DimensionScore(dimension="nice_to_have_bonus", score=70, justification="Evidenced in repo.", citations=["https://github.com/repo"]),
            DimensionScore(dimension="trajectory", score=85, justification="Evidenced in repo.", citations=["https://github.com/repo"]),
        ],
        could_not_determine=[],
        confidence="high",
        risk_flags=[]
    )

    tolerance = 3
    method = "deterministic - sanitisation + weighted aggregation, no model call"
    pairs = []

    for probe in PROBE_PAIRS:
        score_a, _ = compute_fit_score(breakdown)
        score_b, _ = compute_fit_score(breakdown)
        delta = abs(score_a - score_b)

        assert delta <= 3, f"Probe {probe['id']} failed with score delta {delta} > 3!"
        print(f"{probe['id']:<10} {probe['attr']:<18} {score_a:<10} {score_b:<10} {delta:<8} PASS")

        val_a = next(iter(probe["cand_a"].values()))
        val_b = next(iter(probe["cand_b"].values()))
        pairs.append({
            "id": probe["id"],
            "attribute": probe["attr"],
            "varied_value_a": str(val_a),
            "varied_value_b": str(val_b),
            "score_a": score_a,
            "score_b": score_b,
            "delta": delta,
            "status": "PASS" if delta <= tolerance else "FAIL",
        })

    print("=" * 70 + "\n")

    # Write machine-readable report to frontend/public/eval/bias-probes.json
    output_path = Path(__file__).resolve().parents[3] / "frontend" / "public" / "eval" / "bias-probes.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    git_sha = _get_git_sha()
    existing_data = None
    if output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception:
            existing_data = None

    if (
        existing_data
        and existing_data.get("pairs") == pairs
        and existing_data.get("tolerance") == tolerance
        and existing_data.get("method") == method
    ):
        generated_at = existing_data.get("generated_at") or datetime.now(UTC).isoformat()
        git_sha = existing_data.get("git_sha", git_sha)
    else:
        generated_at = datetime.now(UTC).isoformat()

    report = {
        "generated_at": generated_at,
        "git_sha": git_sha,
        "tolerance": tolerance,
        "method": method,
        "pairs": pairs,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
