# Auditor Agent Plan (24 Hours, USD)

## Goal

Build the Auditor Agent that takes:

- `policy_json` from the Policy Agent
- `bill_json` from the Bill Vision Agent

and returns per-line audit results:

- `approved`
- `rejected`
- `partial`
- `warning`

All amounts are represented in USD.

## Code Structure (Entity + Service)

Member C implementation is organized as:

- `auditor/entities/`
  - Agent entities:
    - `base_agent_entity.py`
    - `auditor_agent_entity.py`
  - Domain entities and data contracts (policy, bill, audit output)
  - Includes `from_dict(...)` parsing helpers
- `auditor/services/`
  - Agent services:
    - `base_agent_service.py`
    - `auditor_agent_service.py`
  - Core business services:
    - semantic matching
    - input validation
    - duplicate detection
    - exclusions and scope checks
    - payout + deductible calculations
- `auditor/models.py`, `auditor/matcher.py`, `auditor/engine.py`
  - Backward-compatible re-export modules for legacy imports

### Quick architecture map

```text
auditor/
  entities/
    base_agent_entity.py
    auditor_agent_entity.py
    base_entity.py
    policy_entity.py
    bill_entity.py
    audit_result_entity.py
    __init__.py
  services/
    base_agent_service.py
    auditor_agent_service.py
    base_service.py
    matcher_service.py
    validation_service.py
    audit_service.py
    __init__.py
  models.py        -> compatibility layer (re-export entities)
  matcher.py       -> compatibility layer (re-export matcher services)
  engine.py        -> compatibility layer (re-export audit service)
```

### Responsibility split inside `services/`

- `AuditorAgentService.execute(...)`: agent-centric entrypoint (`policy_json`, `bill_json`)
- `audit_invoice(...)`: top-level orchestration for one invoice
- `KeywordSemanticMatcher`: default semantic matcher (replaceable by LLM)
- `_validate_inputs(...)`: schema/data guardrails
- `_detect_duplicates(...)`: duplicate line-item detection
- `_evaluate_line(...)`: per-line decision (status + amounts + reasons)
- `_apply_invoice_deductible(...)`: invoice-level deductible allocation

## Locked JSON Contracts

### Policy Input (from Agent A)

```json
{
  "meta": {
    "currency": "USD",
    "deductible": 500,
    "coinsurance": 0.8
  },
  "coverage_categories": [
    {
      "id": "diagnostic_imaging",
      "name": "Diagnostic Imaging",
      "coverage_rate": 0.8,
      "per_item_limit": 2000,
      "scope": "all_conditions",
      "clauses": [{ "id": "4.2.1", "text": "..." }]
    }
  ],
  "exclusions": [
    { "id": "excl_cosmetic", "name": "Cosmetic procedures", "clauses": [{ "id": "5.1.3", "text": "..." }] }
  ]
}
```

### Bill Input (from Agent B)

```json
{
  "invoice_meta": {
    "diagnosis": "Motorbike accident"
  },
  "line_items": [
    {
      "id": "line_1",
      "item_name": "Computed Tomography (CT) Scan",
      "quantity": 1,
      "unit_cost": 1200,
      "total_cost": 1200
    }
  ]
}
```

### Auditor Output (to Agent D / UI)

```json
{
  "line_results": [
    {
      "line_id": "line_1",
      "item_name": "Computed Tomography (CT) Scan",
      "matched_policy_category_id": "diagnostic_imaging",
      "status": "approved",
      "allowed_amount": 960,
      "patient_responsible_amount": 240,
      "flags": [],
      "applied_clauses": [{ "id": "4.2.1", "snippet": "..." }],
      "reason": "Approved under Diagnostic Imaging (Clause 4.2.1) at 80% coverage."
    }
  ],
  "summary": {
    "total_invoice_amount": 1200,
    "total_approved": 960,
    "total_patient_responsible": 240,
    "currency": "USD"
  }
}
```

## 24-Hour Execution Plan

### Hour 0-2: Contracts and acceptance criteria

1. Confirm the exact JSON schema with Members A, B, and D.
2. Freeze the status enum: `approved | rejected | partial | warning`.
3. Define success criteria for three demo scenarios:
   - Out-of-scope expense detection
   - Limit alert
   - Duplicate detection

### Hour 2-5: Deterministic calculation core

1. Implement duplicate detection:
   - Same normalized item name + unit cost on same invoice.
2. Implement coverage decision fallback rules:
   - unknown category -> rejected
   - excluded item -> rejected
3. Implement financial calculation:
   - base payout = `covered_amount * coverage_rate`
   - patient = `line_total - payout`
4. Implement status rules:
   - approved: fully eligible and within limits
   - partial: eligible but reduced by limits/deductible
   - rejected: not covered or excluded
   - warning: suspicious duplicate or low confidence semantic match

### Hour 5-8: Deductible and limits

1. Add per-item limit handling:
   - `covered_amount = min(line_total, per_item_limit)`
2. Add deductible logic at invoice level (for hackathon speed):
   - `final_payout = max(0, raw_total_payout - deductible)`
3. Proportionally distribute deductible impact across approved/partial lines.

### Hour 8-12: LLM semantic matcher

1. Build `match_line_to_policy_category(line_item, policy)` function.
2. Prompt the LLM with:
   - policy categories
   - exclusions
   - diagnosis context
3. Enforce strict JSON output:
   - `category_id`
   - `exclusion_id`
   - `reason`
   - `confidence`

### Hour 12-16: Clause-grounded explanations

1. For each decision, attach top relevant clause IDs.
2. Generate concise explanation strings:
   - include clause references
   - include why status is approved/rejected/partial/warning
3. Guarantee explanations are 1-2 sentences for UI readability.

### Hour 16-20: Scenario validation

1. Out-of-scope case:
   - accident-only policy; non-accident diagnosis -> rejected
2. Limit alert:
   - room charge above policy cap -> partial + over-limit flag
3. Duplicate detection:
   - repeated line item -> warning (or rejected per business rule)

### Hour 20-24: Integration and demo hardening

1. Hand final output JSON examples to Member D for UI mapping.
2. Run end-to-end smoke test with one real policy and one real invoice.
3. Add guardrails for missing fields and model uncertainty.
4. Final demo dry run with narrative:
   - what was billed
   - what is covered
   - why (clause)
   - who pays what (USD)

## Core Formula

Use this as baseline:

`Payout = (Eligible Amount - Deductible Allocation) * Coverage Rate`

Where:

- `Eligible Amount` is limited by policy caps.
- Deductible is applied once per invoice and allocated proportionally.

## Suggested branch workflow

```bash
git checkout -b feature/auditor-agent-usd
```

## Member C Completion Checklist (Hackathon Ready)

Use this as the final gate before demo day.

### C1 - Auditor core (must be done)

- [ ] `audit_invoice(policy, bill)` runs end-to-end with no crashes.
- [ ] All four statuses are reachable: `approved`, `rejected`, `partial`, `warning`.
- [ ] Exclusion detection is working and cites clause IDs.
- [ ] Out-of-scope logic for `accident_only` is tested.
- [ ] Duplicate detection is tested.
- [ ] Deductible and limit math are consistent in USD.

### C2 - Integration contracts (must be aligned with A/B/D)

- [ ] Policy Agent output matches the schema in this doc exactly.
- [ ] Bill Vision Agent output includes `diagnosis` and stable line item fields.
- [ ] Frontend maps each status to color/tag consistently.
- [ ] Frontend displays `reason` and `applied_clauses` per line.
- [ ] Frontend summary totals match backend output fields.

### C3 - Demo scenario pack (must be prepared)

- [ ] Scenario 1: out-of-scope expense (`accident_only` mismatch)
- [ ] Scenario 2: limit exceeded (partial payout with over-limit flag)
- [ ] Scenario 3: duplicate service line item (warning/rejected per team policy)

### C4 - Nice-to-have fine tuning

- [ ] Replace keyword matcher with LLM matcher (keep keyword fallback).
- [ ] Add confidence threshold and manual-review path.
- [ ] Improve duplicate logic with item code + fuzzy name matching.
- [ ] Tighten exclusion matching to reduce false positives.
- [ ] Add a small evaluation set (10-20 labeled lines) to quickly score precision.

## Team Sync Template (Hour 6 and Hour 18)

Run these two sync checkpoints as mandatory.

### Hour 6 - Contract lock

- Confirm final JSON keys and types.
- Confirm status semantics (`warning` vs `rejected` for duplicates).
- Confirm clause citation format (`Clause X.Y.Z`).

### Hour 18 - End-to-end smoke test

- Run one real policy + one real invoice through A -> B -> C -> D.
- Verify no crashes and no missing fields.
- Verify each line has status + reason + amount.
- Log every mismatch and assign owner immediately.
