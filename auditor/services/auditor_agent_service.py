from __future__ import annotations

from auditor.entities import AuditResult, AuditorAgentEntity, Bill, Policy
from auditor.services.audit_service import audit_invoice
from auditor.services.base_agent_service import BaseAgentService
from auditor.services.base_service import SemanticMatcher


class AuditorAgentService(BaseAgentService):
    def __init__(
        self,
        entity: AuditorAgentEntity,
        matcher: SemanticMatcher | None = None,
    ) -> None:
        super().__init__(entity=entity)
        self.matcher = matcher

    @property
    def agent(self) -> AuditorAgentEntity:
        return self.entity

    def execute(self, policy_json: dict, bill_json: dict) -> AuditResult:
        self.agent.mark_running()
        try:
            policy = Policy.from_dict(policy_json)
            bill = Bill.from_dict(bill_json)
            result = self.execute_from_entities(policy=policy, bill=bill)
            self.agent.mark_completed()
            self.agent.last_summary = {
                "total_invoice_amount": result.summary.total_invoice_amount,
                "total_approved": result.summary.total_approved,
                "total_patient_responsible": result.summary.total_patient_responsible,
                "currency": result.summary.currency,
            }
            return result
        except Exception as exc:  # pragma: no cover - defensive path
            self.agent.mark_failed(str(exc))
            raise

    def execute_from_entities(self, policy: Policy, bill: Bill) -> AuditResult:
        return audit_invoice(
            policy=policy,
            bill=bill,
            matcher=self.matcher,
            low_match_confidence_threshold=self.agent.low_match_confidence_threshold,
            duplicate_status=self.agent.duplicate_handling,
        )
