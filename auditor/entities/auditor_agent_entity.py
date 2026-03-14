from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from auditor.entities.base_agent_entity import BaseAgentEntity


DuplicateHandling = Literal["warning", "rejected"]


@dataclass
class AuditorAgentEntity(BaseAgentEntity):
    currency: str = "USD"
    low_match_confidence_threshold: float = 0.5
    duplicate_handling: DuplicateHandling = "warning"
    strict_currency_check: bool = True
    matcher_name: str = "KeywordSemanticMatcher"
    last_summary: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build_default(cls) -> "AuditorAgentEntity":
        return cls(
            agent_id="auditor-agent-c",
            agent_name="Auditor Agent",
            version="v1",
            description=(
                "Cross-checks policy and bill data, then returns per-line payout "
                "decisions with status, amounts, and clause-grounded reasons."
            ),
            input_contract={
                "policy_json": {
                    "meta": "currency, deductible, coinsurance",
                    "coverage_categories": "id, name, coverage_rate, scope, clauses",
                    "exclusions": "id, name, clauses",
                },
                "bill_json": {
                    "invoice_meta": "diagnosis, date, hospital_name",
                    "line_items": "id, item_name, item_code, quantity, unit_cost, total_cost",
                },
            },
            output_contract={
                "line_results": "status, allowed_amount, patient_responsible_amount, reason, flags",
                "summary": "total_invoice_amount, total_approved, total_patient_responsible, currency",
            },
        )
