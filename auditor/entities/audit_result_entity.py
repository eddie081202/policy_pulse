from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


AuditStatus = Literal["approved", "rejected", "partial", "warning"]


@dataclass
class AppliedClause:
    id: str
    snippet: str = ""


@dataclass
class LineAuditResult:
    line_id: str
    item_name: str
    matched_policy_category_id: str | None
    status: AuditStatus
    allowed_amount: float
    patient_responsible_amount: float
    flags: list[str] = field(default_factory=list)
    applied_clauses: list[AppliedClause] = field(default_factory=list)
    reason: str = ""
    line_total_cost: float = 0.0


@dataclass
class AuditSummary:
    total_invoice_amount: float
    total_approved: float
    total_patient_responsible: float
    currency: str = "USD"
    notes: str = ""


@dataclass
class AuditResult:
    line_results: list[LineAuditResult]
    summary: AuditSummary

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
