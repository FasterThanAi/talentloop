from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Dimension:
    key: str
    weight: float
    description: str


RUBRIC_VERSION = "v1"

RUBRIC_V1: list[Dimension] = [
    Dimension(
        key="must_have_coverage",
        weight=0.40,
        description="Evidence for each must-have skill and requirement"
    ),
    Dimension(
        key="depth_of_experience",
        weight=0.25,
        description="Depth vs. surface familiarity (shipped & maintained vs used once)"
    ),
    Dimension(
        key="domain_relevance",
        weight=0.15,
        description="Relevance of demonstrated background to role domain"
    ),
    Dimension(
        key="nice_to_have_bonus",
        weight=0.10,
        description="Nice-to-have skills evidenced in public projects"
    ),
    Dimension(
        key="trajectory",
        weight=0.10,
        description="Growth, ownership scope, and technical leadership trajectory"
    ),
]

# Invariant: weights must sum strictly to 1.0
_total_weight = sum(dim.weight for dim in RUBRIC_V1)
assert abs(_total_weight - 1.0) < 1e-6, f"Rubric weights must sum to 1.0, got {_total_weight}"

DIMENSION_MAP = {dim.key: dim for dim in RUBRIC_V1}
