from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from auditor.entities import Bill, LineItem, Policy


@dataclass
class MatchResult:
    category_id: str | None
    exclusion_id: str | None
    confidence: float
    reason: str


class SemanticMatcher(Protocol):
    def match_line(self, line_item: LineItem, bill: Bill, policy: Policy) -> MatchResult:
        ...
