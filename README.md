# Policy Pulse - Bill Auditor

Policy Pulse is a hackathon project that audits medical bills against insurance policies using a 3-agent architecture:

- Policy Agent: parses policy PDFs and builds structured policy data.
- Bill Vision Agent: extracts invoice line items from bill images.
- Auditor Agent: semantically matches bill items to policy clauses and computes payout outcomes.

This repository currently focuses on the Auditor side and integration-ready planning.

## Currency Convention

All examples and calculations in this project use USD.

## Auditor Scaffold

This repo now includes a hackathon-ready Auditor scaffold:

- `auditor/entities/`: domain entities (policy, bill, and audit result contracts).
- `auditor/services/`: matching + decision services (semantic match, validation, payout logic).
- `auditor/models.py`, `auditor/matcher.py`, `auditor/engine.py`: compatibility re-export modules.
- `auditor/sample_data.py`: sample policy and bill payloads in USD.
- `run_auditor_demo.py`: local smoke test that prints audit JSON.

## Auditor Architecture

The Auditor Agent (`Member C`) is implemented in an agent-centric style:

1. Agent entities (`auditor/entities/`)
   - `BaseAgentEntity` stores generic agent metadata/state.
   - `AuditorAgentEntity` stores Auditor-specific attributes (currency, thresholds, behavior).
2. Input/Output contracts (`auditor/entities/auditor_agent_entity.py`)
   - Keeps agent-owned payload contracts and conversion helpers in one place.
   - Defines stable input/output schema for frontend rendering.
3. Agent services (`auditor/services/`)
   - `BaseAgentService` defines service-level execution contract.
   - `AuditorAgentService` orchestrates end-to-end execution for this agent entity.
4. Semantic matching (`auditor/services/auditor_agent_service.py`)
   - Uses a pluggable `SemanticMatcher` interface.
   - Current implementation is keyword-based for offline demo reliability.
   - Can be replaced with an LLM-backed matcher without touching payout logic.
5. Decision + calculation engine (`auditor/services/auditor_agent_service.py`)
   - Duplicate detection.
   - Exclusion and scope checks.
   - Input schema validation with clear failure messages.
   - Per-item policy limits and coverage-rate payout math.
   - Invoice-level deductible allocation.
   - Final line-item statuses and reason strings with clause references.

### Current Module Map

```text
auditor/
  entities/
    base_agent_entity.py
    auditor_agent_entity.py
    __init__.py     # export all agent-owned contracts
  services/
    base_agent_service.py
    auditor_agent_service.py
    __init__.py     # export agent service entrypoints
  models.py        # Compatibility re-export -> entities/
  matcher.py       # Compatibility re-export -> services/
  engine.py        # Compatibility re-export -> services/
  sample_data.py   # Demo policy/bill payloads
```

### Service Entry Points

- Main public function: `auditor.services.audit_invoice(policy, bill, matcher=None)`
- Main agent-centric service: `auditor.services.AuditorAgentService`
- Main agent-centric entity: `auditor.entities.AuditorAgentEntity`
- Main matcher interface: `auditor.services.SemanticMatcher`
- Default matcher implementation: `auditor.services.KeywordSemanticMatcher`
- Optional LLM matcher: `auditor.services.LLMSemanticMatcher`

## Fine-Tuning Notes

Current baseline includes practical safeguards for hackathon demos:

- Strict input validation before audit execution.
- Duplicate detection prefers `item_code` when available.
- Exclusion matching uses stronger token rules to reduce false positives.
- Currency in output summary follows policy meta (USD required by this project).
- LLM matcher is optional and automatically falls back to keyword matcher if API config is missing or fails.

### Enable LLM Matcher (Optional)

To use LLM semantic matching while keeping the same flow:

1. Set `AuditorAgentEntity.matcher_name = "LLMSemanticMatcher"`.
2. Configure model settings on the entity (`llm_model`, `llm_base_url`, `llm_api_key_env`).
3. Export your API key in the environment variable specified by `llm_api_key_env` (default: `OPENAI_API_KEY`).

If the LLM call fails at runtime, the system falls back to `KeywordSemanticMatcher` automatically.

## Processing Flow

1. Load `policy_json` and `bill_json`.
2. Detect duplicate line items.
3. Match each bill line item to a policy category (or exclusion).
4. Apply out-of-scope rules (for example, `accident_only`).
5. Compute allowed amount and patient responsibility.
6. Apply deductible once at invoice level.
7. Return `line_results`, `summary`, and `utilization_report` in USD.

## Data Contract Summary

- Policy input must provide:
  - `meta.currency`, `meta.deductible`, `meta.coinsurance`
  - `coverage_categories[]` with `id`, `name`, `coverage_rate`, `scope`, and `clauses[]`
  - Optional score tuning fields per category: `premium_score` (0-100)
  - Optional upgrade simulation fields per category: `upgrade_premium_cost`, `upgrade_coverage_rate`
  - `exclusions[]` with `id`, `name`, and `clauses[]`
- Bill input must provide:
  - `invoice_meta.diagnosis` (required for scope checks)
  - `line_items[]` with `item_name`, `unit_cost`, and `total_cost`
- Auditor output provides:
  - Per-line `status` (`approved | rejected | partial | warning`)
  - `allowed_amount`, `patient_responsible_amount`
  - `flags`, `reason`, and `applied_clauses`
  - Aggregated summary totals in USD
  - `utilization_report.category_scores[]` (premium/coverage/utilization/category total)
  - `utilization_report.overall_utilization_score` and `overall_recommendation`
  - `utilization_report.upgrade_recommendations[]` with `worth_it` decision

## Integration Dependencies

The Auditor core is functionally ready, but full end-to-end demo quality depends on:

- Policy Agent (A): stable clause and category extraction quality
- Bill Vision Agent (B): consistent line-item JSON and diagnosis extraction
- Frontend/Integration (D): status visualization and final table mapping

## Quick Run

```bash
python run_auditor_demo.py
```
