import json

from auditor.entities import AuditorAgentEntity
from auditor.services import AuditorAgentService
from auditor.sample_data import SAMPLE_BILL, SAMPLE_POLICY


def main() -> None:
    agent_entity = AuditorAgentEntity.build_default()
    agent_entity.matcher_name = "LLMSemanticMatcher"
    agent_entity.llm_model = "gpt-4o-mini"
    agent_entity.llm_base_url = "https://api.openai.com/v1"
    agent_entity.llm_api_key_env = "OPENAI_API_KEY"
    agent_entity.llm_timeout_seconds = 20
    agent_entity.llm_temperature = 0.0
    agent_service = AuditorAgentService(entity=agent_entity)
    result = agent_service.execute(policy_json=SAMPLE_POLICY, bill_json=SAMPLE_BILL)
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
