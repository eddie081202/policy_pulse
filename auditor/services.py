from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from auditor.entities import (
    AppliedClause,
    AuditResult,
    AuditSummary,
    Bill,
    CoverageCategory,
    Exclusion,
    LineAuditResult,
    LineItem,
    Policy,
)


@dataclass
class MatchResult:
    category_id: str | None
    exclusion_id: str | None
    confidence: float
    reason: str


class SemanticMatcher(Protocol):
    def match_line(self, line_item: LineItem, bill: Bill, policy: Policy) -> MatchResult:
        ...


class KeywordSemanticMatcher:
    """
    Fast deterministic matcher for hackathon scaffolding.
    Replace this with an LLM-backed matcher when API keys are ready.
    """

    def match_line(self, line_item: LineItem, bill: Bill, policy: Policy) -> MatchResult:
        item_text = _normalize(line_item.item_name)
        item_tokens = set(item_text.split())

        exclusion = _find_exclusion_match(item_tokens, policy.exclusions)
        if exclusion is not None:
            return MatchResult(
                category_id=None,
                exclusion_id=exclusion.id,
                confidence=0.95,
                reason=f"Item matches exclusion: {exclusion.name}.",
            )

        best_category_id = None
        best_score = -1
        for category in policy.coverage_categories:
            candidate_text = _normalize(
                f"{category.name} {category.description} {line_item.category_hint}"
            )
            score = _token_overlap_score(item_text, candidate_text)
            if score > best_score:
                best_score = score
                best_category_id = category.id

        if best_category_id is None or best_score <= 0:
            return MatchResult(
                category_id=None,
                exclusion_id=None,
                confidence=0.2,
                reason="No strong policy category match found.",
            )

        confidence = min(0.99, 0.45 + (best_score * 0.15))
        return MatchResult(
            category_id=best_category_id,
            exclusion_id=None,
            confidence=confidence,
            reason=f"Best keyword similarity match score: {best_score}.",
        )


def audit_invoice(
    policy: Policy,
    bill: Bill,
    matcher: SemanticMatcher | None = None,
) -> AuditResult:
    _validate_inputs(policy, bill)
    active_matcher = matcher or KeywordSemanticMatcher()
    duplicates = _detect_duplicates(bill)

    line_results: list[LineAuditResult] = []
    for line in bill.line_items:
        if duplicates.get(line.id, False):
            line_results.append(
                LineAuditResult(
                    line_id=line.id,
                    item_name=line.item_name,
                    matched_policy_category_id=None,
                    status="warning",
                    allowed_amount=0.0,
                    patient_responsible_amount=round(line.total_cost, 2),
                    flags=["duplicate"],
                    applied_clauses=[],
                    reason="Potential duplicate service line item detected; review required.",
                    line_total_cost=round(line.total_cost, 2),
                )
            )
            continue

        match = active_matcher.match_line(line, bill, policy)
        line_results.append(_evaluate_line(policy, bill, line, match))

    _apply_invoice_deductible(policy, line_results)

    summary = AuditSummary(
        total_invoice_amount=round(sum(x.line_total_cost for x in line_results), 2),
        total_approved=round(sum(x.allowed_amount for x in line_results), 2),
        total_patient_responsible=round(
            sum(x.patient_responsible_amount for x in line_results), 2
        ),
        currency=policy.meta.currency or "USD",
        notes=(
            f"All values are in {policy.meta.currency or 'USD'}. "
            "Deductible applied once per invoice."
        ),
    )
    return AuditResult(line_results=line_results, summary=summary)


def _evaluate_line(
    policy: Policy,
    bill: Bill,
    line: LineItem,
    match: MatchResult,
) -> LineAuditResult:
    category = _get_category(policy, match.category_id)

    if match.exclusion_id is not None:
        exclusion = _get_exclusion_clause(policy, match.exclusion_id)
        return LineAuditResult(
            line_id=line.id,
            item_name=line.item_name,
            matched_policy_category_id=None,
            status="rejected",
            allowed_amount=0.0,
            patient_responsible_amount=round(line.total_cost, 2),
            flags=["excluded"],
            applied_clauses=exclusion,
            reason=f"Rejected because this item is excluded under policy terms. {match.reason}",
            line_total_cost=round(line.total_cost, 2),
        )

    if category is None:
        return LineAuditResult(
            line_id=line.id,
            item_name=line.item_name,
            matched_policy_category_id=None,
            status="rejected",
            allowed_amount=0.0,
            patient_responsible_amount=round(line.total_cost, 2),
            flags=["not_covered"],
            applied_clauses=[],
            reason=f"Rejected because no policy category applies. {match.reason}",
            line_total_cost=round(line.total_cost, 2),
        )

    if _is_out_of_scope(category.scope, bill.invoice_meta.diagnosis):
        clause_refs = _to_applied_clauses(category)
        return LineAuditResult(
            line_id=line.id,
            item_name=line.item_name,
            matched_policy_category_id=category.id,
            status="rejected",
            allowed_amount=0.0,
            patient_responsible_amount=round(line.total_cost, 2),
            flags=["out_of_scope"],
            applied_clauses=clause_refs,
            reason=(
                f"Rejected because '{category.name}' is accident-only, while diagnosis "
                "does not look accident-related."
            ),
            line_total_cost=round(line.total_cost, 2),
        )

    line_total = float(line.total_cost)
    capped_amount = line_total
    flags: list[str] = []
    status = "approved"

    if category.per_item_limit is not None and line_total > category.per_item_limit:
        capped_amount = category.per_item_limit
        flags.append("over_limit")
        status = "partial"

    rate = category.coverage_rate if category.coverage_rate > 0 else policy.meta.coinsurance
    allowed = round(max(0.0, capped_amount * rate), 2)
    patient = round(max(0.0, line_total - allowed), 2)

    # For uncertain semantic matches, downgrade to warning while preserving math.
    if match.confidence < 0.5:
        status = "warning"
        flags.append("low_match_confidence")

    reason = _build_reason(category, status, flags, match.reason)
    return LineAuditResult(
        line_id=line.id,
        item_name=line.item_name,
        matched_policy_category_id=category.id,
        status=status,
        allowed_amount=allowed,
        patient_responsible_amount=patient,
        flags=flags,
        applied_clauses=_to_applied_clauses(category),
        reason=reason,
        line_total_cost=round(line_total, 2),
    )


def _build_reason(
    category: CoverageCategory,
    status: str,
    flags: list[str],
    match_reason: str,
) -> str:
    clause_id = category.clauses[0].id if category.clauses else "N/A"
    if status == "approved":
        return f"Approved under '{category.name}' (Clause {clause_id}). {match_reason}"
    if status == "partial":
        return (
            f"Partially covered under '{category.name}' due to policy limits "
            f"(Clause {clause_id}). {match_reason}"
        )
    if status == "warning":
        return (
            f"Coverage mapped to '{category.name}' but requires manual review "
            f"(Clause {clause_id}). Flags: {', '.join(flags)}."
        )
    return f"Decision linked to '{category.name}' (Clause {clause_id})."


def _detect_duplicates(bill: Bill) -> dict[str, bool]:
    seen: set[tuple[str, float]] = set()
    duplicates: dict[str, bool] = {}

    for line in bill.line_items:
        code = (line.item_code or "").strip().lower()
        if code:
            key = (f"code:{code}", float(line.unit_cost))
        else:
            key = (_normalize(line.item_name), float(line.unit_cost))
        if key in seen:
            duplicates[line.id] = True
        else:
            duplicates[line.id] = False
            seen.add(key)
    return duplicates


def _apply_invoice_deductible(policy: Policy, line_results: list[LineAuditResult]) -> None:
    deductible = max(0.0, float(policy.meta.deductible))
    if deductible <= 0:
        return

    eligible_lines = [
        x
        for x in line_results
        if x.status in ("approved", "partial", "warning") and x.allowed_amount > 0
    ]
    raw_total = sum(x.allowed_amount for x in eligible_lines)
    if raw_total <= 0:
        return

    if deductible >= raw_total:
        for line in eligible_lines:
            reduction = line.allowed_amount
            line.patient_responsible_amount = round(
                line.patient_responsible_amount + line.allowed_amount, 2
            )
            line.allowed_amount = 0.0
            if line.status == "approved":
                line.status = "partial"
                line.reason = (
                    "Partially covered after deductible adjustment at invoice level. "
                    + line.reason
                )
            if reduction > 0 and "deductible_applied" not in line.flags:
                line.flags.append("deductible_applied")
        return

    for line in eligible_lines:
        share = line.allowed_amount / raw_total
        reduction = round(deductible * share, 2)
        line.allowed_amount = round(max(0.0, line.allowed_amount - reduction), 2)
        line.patient_responsible_amount = round(line.line_total_cost - line.allowed_amount, 2)
        if reduction > 0 and "deductible_applied" not in line.flags:
            line.flags.append("deductible_applied")
        if line.status == "approved":
            line.status = "partial"
            line.reason = (
                "Partially covered after deductible adjustment at invoice level. "
                + line.reason
            )


def _get_category(policy: Policy, category_id: str | None) -> CoverageCategory | None:
    if category_id is None:
        return None
    for category in policy.coverage_categories:
        if category.id == category_id:
            return category
    return None


def _get_exclusion_clause(policy: Policy, exclusion_id: str) -> list[AppliedClause]:
    for exclusion in policy.exclusions:
        if exclusion.id == exclusion_id:
            return [AppliedClause(id=x.id, snippet=x.text) for x in exclusion.clauses[:1]]
    return []


def _to_applied_clauses(category: CoverageCategory) -> list[AppliedClause]:
    return [AppliedClause(id=x.id, snippet=x.text) for x in category.clauses[:1]]


def _is_out_of_scope(scope: str, diagnosis: str) -> bool:
    if scope.strip().lower() != "accident_only":
        return False

    diagnosis_text = _normalize(diagnosis)
    accident_words = {"accident", "trauma", "injury", "collision", "fracture"}
    return not any(word in diagnosis_text.split() for word in accident_words)


def _validate_inputs(policy: Policy, bill: Bill) -> None:
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


def _find_exclusion_match(item_tokens: set[str], exclusions: list[Exclusion]) -> Exclusion | None:
    for exclusion in exclusions:
        corpus = _normalize(f"{exclusion.name} {exclusion.text}")
        exclusion_tokens = set(corpus.split())
        overlap_tokens = item_tokens & exclusion_tokens
        # Reduce false positives by requiring stronger evidence for exclusions.
        if _is_strong_exclusion_match(overlap_tokens):
            return exclusion
    return None


def _token_overlap_score(a: str, b: str) -> int:
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    # Keep short medical acronyms like CT/MRI while still removing single letters.
    a_tokens = {t for t in a_tokens if len(t) > 1}
    b_tokens = {t for t in b_tokens if len(t) > 1}
    return len(a_tokens & b_tokens)


def _normalize(value: str) -> str:
    cleaned = []
    for ch in value.lower():
        cleaned.append(ch if ch.isalnum() else " ")
    return " ".join("".join(cleaned).split())


def _is_strong_exclusion_match(overlap_tokens: set[str]) -> bool:
    if not overlap_tokens:
        return False
    stopwords = {
        "and",
        "for",
        "the",
        "with",
        "care",
        "service",
        "services",
        "medical",
        "hospital",
        "treatment",
    }
    informative = {t for t in overlap_tokens if t not in stopwords}
    if len(informative) >= 2:
        return True
    return any(len(t) >= 7 for t in informative)
