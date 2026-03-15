from __future__ import annotations

from dataclasses import dataclass


@dataclass
class JudgeEntity:
    price_weight: float = 0.4
    policy_utilization_weight: float = 0.2
    coverage_weight: float = 0.2
    relative_policy_quality_weight: float = 0.2
    top_alternatives: int = 3

