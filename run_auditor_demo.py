import json

from auditor.entities import AuditorAgentEntity
from auditor.services import AuditorAgentService
from auditor.sample_data import SAMPLE_BILL, SAMPLE_POLICY


def main() -> None:
    agent_entity = AuditorAgentEntity.build_default()
    agent_service = AuditorAgentService(entity=agent_entity)
    result = agent_service.execute(policy_json=SAMPLE_POLICY, bill_json=SAMPLE_BILL)
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
