from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Protocol
from urllib import error, request

from auditor.entities import (
    AppliedClause,
    AuditResult,
    AuditSummary,
    AuditorAgentEntity,
    Bill,
    CategoryUtilizationScore,
    CoverageCategory,
    Exclusion,
    LineAuditResult,
    LineItem,
    Policy,
    UpgradeRecommendation,
    UtilizationReport,
)
from auditor.services.base_agent_service import BaseAgentService


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


class LLMSemanticMatcher:
    """
    Optional LLM matcher with keyword fallback.
    Uses an OpenAI-compatible chat completions endpoint.
    """

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key_env: str,
        timeout_seconds: int = 20,
        temperature: float = 0.0,
        fallback_matcher: KeywordSemanticMatcher | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.fallback_matcher = fallback_matcher or KeywordSemanticMatcher()

    def match_line(self, line_item: LineItem, bill: Bill, policy: Policy) -> MatchResult:
        api_key = os.getenv(self.api_key_env, "")
        if not api_key:
            fallback = self.fallback_matcher.match_line(line_item, bill, policy)
            return MatchResult(
                category_id=fallback.category_id,
                exclusion_id=fallback.exclusion_id,
                confidence=fallback.confidence,
                reason=(
                    f"{fallback.reason} LLM disabled because "
                    f"environment variable '{self.api_key_env}' is not set."
                ),
            )

        try:
            llm_response = self._call_llm(
                api_key=api_key,
                line_item=line_item,
                bill=bill,
                policy=policy,
            )
            parsed = self._parse_llm_response(llm_response, policy)
            return parsed
        except Exception as exc:
            fallback = self.fallback_matcher.match_line(line_item, bill, policy)
            return MatchResult(
                category_id=fallback.category_id,
                exclusion_id=fallback.exclusion_id,
                confidence=fallback.confidence,
                reason=f"{fallback.reason} LLM fallback triggered: {exc}",
            )

    def _call_llm(self, api_key: str, line_item: LineItem, bill: Bill, policy: Policy) -> str:
        categories = [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "scope": c.scope,
                "coverage_rate": c.coverage_rate,
            }
            for c in policy.coverage_categories
        ]
        exclusions = [
            {"id": e.id, "name": e.name, "text": e.text}
            for e in policy.exclusions
        ]
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an insurance claim semantic matching engine. "
                        "Return only JSON with keys: category_id, exclusion_id, confidence, reason. "
                        "If no match, set category_id to null. "
                        "If excluded, set exclusion_id to the best exclusion id."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "policy": {
                                "categories": categories,
                                "exclusions": exclusions,
                            },
                            "invoice_context": {
                                "diagnosis": bill.invoice_meta.diagnosis,
                                "visit_reason": bill.invoice_meta.visit_reason,
                            },
                            "line_item": {
                                "item_name": line_item.item_name,
                                "item_code": line_item.item_code,
                                "category_hint": line_item.category_hint,
                                "quantity": line_item.quantity,
                                "unit_cost": line_item.unit_cost,
                                "total_cost": line_item.total_cost,
                            },
                        }
                    ),
                },
            ],
        }

        raw_payload = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=f"{self.base_url}/chat/completions",
            data=raw_payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                body = resp.read().decode("utf-8")
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM HTTP error {exc.code}: {body}") from exc

        data = json.loads(body)
        return str(data["choices"][0]["message"]["content"])

    def _parse_llm_response(self, content: str, policy: Policy) -> MatchResult:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("LLM response does not contain a JSON object")

        parsed = json.loads(content[start : end + 1])
        category_id = parsed.get("category_id")
        exclusion_id = parsed.get("exclusion_id")
        confidence = _safe_float(parsed.get("confidence", 0.5), default=0.5)
        reason = str(parsed.get("reason", "LLM semantic match result"))

        valid_category_ids = {c.id for c in policy.coverage_categories}
        valid_exclusion_ids = {e.id for e in policy.exclusions}
        if category_id is not None and category_id not in valid_category_ids:
            raise ValueError(f"Invalid category_id from LLM: {category_id}")
        if exclusion_id is not None and exclusion_id not in valid_exclusion_ids:
            raise ValueError(f"Invalid exclusion_id from LLM: {exclusion_id}")

        return MatchResult(
            category_id=category_id,
            exclusion_id=exclusion_id,
            confidence=max(0.0, min(1.0, confidence)),
            reason=reason,
        )


class AuditorAgentService(BaseAgentService):
    def __init__(
        self,
        entity: AuditorAgentEntity,
        matcher: SemanticMatcher | None = None,
    ) -> None:
        super().__init__(entity=entity)
        self.matcher = matcher or self._build_matcher()

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
                "overall_utilization_score": (
                    result.utilization_report.overall_utilization_score
                    if result.utilization_report is not None
                    else None
                ),
            }
            return result
        except Exception as exc:  # pragma: no cover - defensive path
            self.agent.mark_failed(str(exc))
            raise

    def execute_from_entities(self, policy: Policy, bill: Bill) -> AuditResult:
        return _audit_invoice(
            policy=policy,
            bill=bill,
            matcher=self.matcher,
            low_match_confidence_threshold=self.agent.low_match_confidence_threshold,
            duplicate_status=self.agent.duplicate_handling,
        )

    def _build_matcher(self) -> SemanticMatcher:
        if self.agent.matcher_name == "LLMSemanticMatcher":
            return LLMSemanticMatcher(
                model=self.agent.llm_model,
                base_url=self.agent.llm_base_url,
                api_key_env=self.agent.llm_api_key_env,
                timeout_seconds=self.agent.llm_timeout_seconds,
                temperature=self.agent.llm_temperature,
                fallback_matcher=KeywordSemanticMatcher(),
            )
        return KeywordSemanticMatcher()


def audit_invoice(
    policy: Policy,
    bill: Bill,
    matcher: SemanticMatcher | None = None,
    low_match_confidence_threshold: float = 0.5,
    duplicate_status: str = "warning",
) -> AuditResult:
    return _audit_invoice(
        policy=policy,
        bill=bill,
        matcher=matcher,
        low_match_confidence_threshold=low_match_confidence_threshold,
        duplicate_status=duplicate_status,
    )


def _audit_invoice(
    policy: Policy,
    bill: Bill,
    matcher: SemanticMatcher | None = None,
    low_match_confidence_threshold: float = 0.5,
    duplicate_status: str = "warning",
) -> AuditResult:
    _validate_inputs(policy, bill)
    active_matcher = matcher or KeywordSemanticMatcher()
    duplicates = _detect_duplicates(bill)
    resolved_duplicate_status = _resolve_duplicate_status(duplicate_status)

    line_results: list[LineAuditResult] = []
    for line in bill.line_items:
        if duplicates.get(line.id, False):
            line_results.append(
                LineAuditResult(
                    line_id=line.id,
                    item_name=line.item_name,
                    matched_policy_category_id=None,
                    status=resolved_duplicate_status,
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
        line_results.append(
            _evaluate_line(
                policy=policy,
                bill=bill,
                line=line,
                match=match,
                low_match_confidence_threshold=low_match_confidence_threshold,
            )
        )

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
    utilization_report = _build_utilization_report(policy=policy, line_results=line_results)
    return AuditResult(
        line_results=line_results,
        summary=summary,
        utilization_report=utilization_report,
    )


def _evaluate_line(
    policy: Policy,
    bill: Bill,
    line: LineItem,
    match: MatchResult,
    low_match_confidence_threshold: float,
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
    if match.confidence < low_match_confidence_threshold:
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
        if category.premium_score is not None and not (0 <= category.premium_score <= 100):
            errors.append(
                f"policy.coverage_categories[{i}].premium_score must be between 0 and 100"
            )
        if category.upgrade_premium_cost is not None and category.upgrade_premium_cost < 0:
            errors.append(
                f"policy.coverage_categories[{i}].upgrade_premium_cost must be >= 0"
            )
        if category.upgrade_coverage_rate is not None and not (
            0 <= category.upgrade_coverage_rate <= 1
        ):
            errors.append(
                f"policy.coverage_categories[{i}].upgrade_coverage_rate must be between 0 and 1"
            )

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


def _resolve_duplicate_status(status: str) -> str:
    return status if status in {"warning", "rejected"} else "warning"


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_utilization_report(policy: Policy, line_results: list[LineAuditResult]) -> UtilizationReport:
    category_scores: list[CategoryUtilizationScore] = []
    upgrade_recommendations: list[UpgradeRecommendation] = []

    weighted_score_sum = 0.0
    weighted_amount_sum = 0.0

    for category in policy.coverage_categories:
        matched_lines = [
            line for line in line_results if line.matched_policy_category_id == category.id
        ]
        total_billed = round(sum(line.line_total_cost for line in matched_lines), 2)
        total_approved = round(sum(line.allowed_amount for line in matched_lines), 2)
        line_count = len(matched_lines)

        coverage_score = round(_clamp_score(category.coverage_rate * 100.0), 2)
        premium_score = (
            round(_clamp_score(category.premium_score), 2)
            if category.premium_score is not None
            else round(_infer_premium_score(total_billed=total_billed, total_approved=total_approved), 2)
        )
        utilization_score = (
            round(_clamp_score((total_approved / total_billed) * 100.0), 2)
            if total_billed > 0
            else 0.0
        )
        category_total_score = round(
            (premium_score + coverage_score + utilization_score) / 3.0, 2
        )

        if total_billed > 0:
            weighted_score_sum += category_total_score * total_billed
            weighted_amount_sum += total_billed

        category_scores.append(
            CategoryUtilizationScore(
                category_id=category.id,
                category_name=category.name,
                premium_score=premium_score,
                coverage_score=coverage_score,
                utilization_score=utilization_score,
                category_total_score=category_total_score,
                total_billed=total_billed,
                total_approved=total_approved,
                line_count=line_count,
                recommendation=_category_recommendation(
                    category_total_score=category_total_score,
                    coverage_score=coverage_score,
                    utilization_score=utilization_score,
                    total_billed=total_billed,
                ),
            )
        )

        if (
            total_billed > 0
            and category.upgrade_premium_cost is not None
            and category.upgrade_coverage_rate is not None
        ):
            additional_cost = round(max(0.0, category.upgrade_premium_cost), 2)
            delta_rate = max(0.0, category.upgrade_coverage_rate - category.coverage_rate)
            estimated_additional_payout = round(total_billed * delta_rate, 2)
            worth_it = estimated_additional_payout > additional_cost
            recommendation = (
                (
                    f"Upgrade looks worth it for '{category.name}': estimated extra payout "
                    f"USD {estimated_additional_payout} is higher than additional cost "
                    f"USD {additional_cost}."
                )
                if worth_it
                else (
                    f"Upgrade may not be worth it for '{category.name}': estimated extra payout "
                    f"USD {estimated_additional_payout} is not higher than additional cost "
                    f"USD {additional_cost}."
                )
            )
            upgrade_recommendations.append(
                UpgradeRecommendation(
                    category_id=category.id,
                    category_name=category.name,
                    additional_cost=additional_cost,
                    estimated_additional_payout=estimated_additional_payout,
                    worth_it=worth_it,
                    recommendation=recommendation,
                )
            )

    if weighted_amount_sum > 0:
        overall = round(weighted_score_sum / weighted_amount_sum, 2)
    elif category_scores:
        overall = round(
            sum(category.category_total_score for category in category_scores)
            / len(category_scores),
            2,
        )
    else:
        overall = 0.0

    return UtilizationReport(
        category_scores=category_scores,
        overall_utilization_score=overall,
        overall_recommendation=_overall_recommendation(overall),
        upgrade_recommendations=upgrade_recommendations,
    )


def _clamp_score(score: float) -> float:
    return max(0.0, min(100.0, score))


def _infer_premium_score(total_billed: float, total_approved: float) -> float:
    if total_billed <= 0:
        return 60.0
    patient_ratio = max(0.0, min(1.0, (total_billed - total_approved) / total_billed))
    return _clamp_score((1.0 - patient_ratio) * 100.0)


def _category_recommendation(
    category_total_score: float,
    coverage_score: float,
    utilization_score: float,
    total_billed: float,
) -> str:
    if total_billed <= 0:
        return "No claim data for this category yet; monitor with more invoices."
    if category_total_score >= 75:
        return "Strong value in this category based on current utilization."
    if category_total_score >= 55:
        if coverage_score < 70:
            return "Moderate value; coverage rate is the main weakness to improve."
        if utilization_score < 60:
            return "Moderate value; current claim usage is low for this category."
        return "Moderate value overall; keep monitoring claim trends."
    return "Low value in this category; consider plan adjustments."


def _overall_recommendation(overall_score: float) -> str:
    if overall_score >= 75:
        return "Overall plan looks worth it for this bill profile."
    if overall_score >= 55:
        return "Overall plan has mixed value; review weak categories before renewal."
    return "Overall plan currently looks low-value for this bill profile."
