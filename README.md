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

- `auditor/models.py`: input/output data models and parsing helpers.
- `auditor/matcher.py`: pluggable semantic matcher interface with keyword-based fallback.
- `auditor/engine.py`: core orchestration, duplicate detection, scope checks, payout math, and statuses.
- `auditor/sample_data.py`: sample policy and bill payloads in USD.
- `run_auditor_demo.py`: local smoke test that prints audit JSON.

## Auditor Architecture

The Auditor Agent (`Member C`) is split into three clear layers:

1. Input/Output contracts (`auditor/models.py`)
   - Parses raw JSON from Policy Agent and Bill Vision Agent into typed objects.
   - Defines stable output schema for frontend rendering.
2. Semantic matching (`auditor/matcher.py`)
   - Uses a pluggable `SemanticMatcher` interface.
   - Current implementation is keyword-based for offline demo reliability.
   - Can be replaced with an LLM-backed matcher without touching payout logic.
3. Decision + calculation engine (`auditor/engine.py`)
   - Duplicate detection.
   - Exclusion and scope checks.
   - Input schema validation with clear failure messages.
   - Per-item policy limits and coverage-rate payout math.
   - Invoice-level deductible allocation.
   - Final line-item statuses and reason strings with clause references.

## Fine-Tuning Notes

Current baseline includes practical safeguards for hackathon demos:

- Strict input validation before audit execution.
- Duplicate detection prefers `item_code` when available.
- Exclusion matching uses stronger token rules to reduce false positives.
- Currency in output summary follows policy meta (USD required by this project).

## Processing Flow

1. Load `policy_json` and `bill_json`.
2. Detect duplicate line items.
3. Match each bill line item to a policy category (or exclusion).
4. Apply out-of-scope rules (for example, `accident_only`).
5. Compute allowed amount and patient responsibility.
6. Apply deductible once at invoice level.
7. Return `line_results` and `summary` in USD.

## Data Contract Summary

- Policy input must provide:
  - `meta.currency`, `meta.deductible`, `meta.coinsurance`
  - `coverage_categories[]` with `id`, `name`, `coverage_rate`, `scope`, and `clauses[]`
  - `exclusions[]` with `id`, `name`, and `clauses[]`
- Bill input must provide:
  - `invoice_meta.diagnosis` (required for scope checks)
  - `line_items[]` with `item_name`, `unit_cost`, and `total_cost`
- Auditor output provides:
  - Per-line `status` (`approved | rejected | partial | warning`)
  - `allowed_amount`, `patient_responsible_amount`
  - `flags`, `reason`, and `applied_clauses`
  - Aggregated summary totals in USD

## Integration Dependencies

The Auditor core is functionally ready, but full end-to-end demo quality depends on:

- Policy Agent (A): stable clause and category extraction quality
- Bill Vision Agent (B): consistent line-item JSON and diagnosis extraction
- Frontend/Integration (D): status visualization and final table mapping

## Quick Run

```bash
python run_auditor_demo.py
```
