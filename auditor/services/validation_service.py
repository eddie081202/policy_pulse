from __future__ import annotations

from auditor.entities import Bill, Policy


def validate_audit_inputs(policy: Policy, bill: Bill) -> None:
    errors: list[str] = []
    if not policy.coverage_categories:
        errors.append("policy.coverage_categories is required and cannot be empty")
    if not bill.line_items:
        errors.append("bill.line_items is required and cannot be empty")
    if (policy.meta.currency or "").strip().upper() != "USD":
        errors.append("policy.meta.currency must be 'USD' for this project")

    for i, category in enumerate(policy.coverage_categories):
        if not category.id:
            errors.append(f"policy.coverage_categories[{i}].id is required")
        if not category.name:
            errors.append(f"policy.coverage_categories[{i}].name is required")
        if category.coverage_rate < 0:
            errors.append(f"policy.coverage_categories[{i}].coverage_rate must be >= 0")

    for i, line in enumerate(bill.line_items):
        if not line.item_name:
            errors.append(f"bill.line_items[{i}].item_name is required")
        if line.total_cost < 0:
            errors.append(f"bill.line_items[{i}].total_cost must be >= 0")
        if line.unit_cost < 0:
            errors.append(f"bill.line_items[{i}].unit_cost must be >= 0")

    if errors:
        raise ValueError("Invalid auditor input: " + "; ".join(errors))
