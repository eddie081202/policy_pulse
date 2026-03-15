from auditor.entities import AuditResult, AuditorAgentEntity, Bill, Policy
from auditor.services import AuditorAgentService

# Singleton entity/service pair for a thin package-level API, mirroring
# the style used in agent_doc_reader/main.py.
_entity = AuditorAgentEntity.build_default()
_service = AuditorAgentService(_entity)


def audit_invoice(
    policy: Policy,
    bill: Bill,
    similar_policies: list[Policy] | None = None,
    user_preference: str | None = None,
) -> AuditResult:
    return _service.audit_invoice(
        policy=policy,
        bill=bill,
        similar_policies=similar_policies,
        user_preference=user_preference,
    )


def audit_invoice_from_json(
    policy_json: dict,
    bill_json: dict,
    similar_policies_json: list[dict] | None = None,
    similar_policy_vectors: list[dict] | None = None,
    user_preference: str | None = None,
) -> AuditResult:
    return _service.execute(
        policy_json=policy_json,
        bill_json=bill_json,
        similar_policies_json=similar_policies_json,
        similar_policy_vectors=similar_policy_vectors,
        user_preference=user_preference,
    )
