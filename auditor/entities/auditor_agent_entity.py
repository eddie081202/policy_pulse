from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Literal

from auditor.entities.base_agent_entity import BaseAgentEntity


AuditStatus = Literal["approved", "rejected", "partial", "warning"]
DuplicateHandling = Literal["warning", "rejected"]
PolicyPreference = Literal["price", "coverage"]


def to_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    if match is None:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


@dataclass
class Clause:
    id: str
    text: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Clause":
        return cls(id=str(raw.get("id", "")), text=str(raw.get("text", "")))


@dataclass
class CoverageCategory:
    id: str
    name: str
    description: str = ""
    coverage_rate: float = 0.0
    per_item_limit: float | None = None
    per_day_limit: float | None = None
    premium_score: float | None = None
    upgrade_premium_cost: float | None = None
    upgrade_coverage_rate: float | None = None
    scope: str = "all_conditions"
    clauses: list[Clause] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any], fallback_rate: float) -> "CoverageCategory":
        rate = raw.get("coverage_rate")
        category_rate = _parse_coverage_rate(rate, fallback_rate=float(fallback_rate))
        name = str(raw.get("name", ""))
        category_id = str(raw.get("id", "")).strip() or _slugify(name)
        raw_clauses = raw.get("clauses")
        if raw_clauses is None:
            raw_clauses = raw.get("core_clauses", [])
        clauses = _parse_clause_list(raw_clauses)
        return cls(
            id=category_id,
            name=name,
            description=str(raw.get("description", "")),
            coverage_rate=category_rate,
            per_item_limit=to_optional_float(raw.get("per_item_limit")),
            per_day_limit=to_optional_float(raw.get("per_day_limit")),
            premium_score=to_optional_float(raw.get("premium_score")),
            upgrade_premium_cost=to_optional_float(raw.get("upgrade_premium_cost")),
            upgrade_coverage_rate=to_optional_float(raw.get("upgrade_coverage_rate")),
            scope=str(raw.get("scope", "all_conditions")),
            clauses=clauses,
        )


@dataclass
class Exclusion:
    id: str
    name: str
    text: str = ""
    clauses: list[Clause] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | str) -> "Exclusion":
        if isinstance(raw, str):
            text = raw.strip()
            return cls(
                id=_slugify(text),
                name=text[:80],
                text=text,
                clauses=[],
            )
        return cls(
            id=str(raw.get("id", "")),
            name=str(raw.get("name", "")),
            text=str(raw.get("text", "")),
            clauses=_parse_clause_list(raw.get("clauses", [])),
        )


@dataclass
class PolicyMeta:
    policy_id: str = ""
    policy_name: str = ""
    currency: str = "USD"
    deductible: float = 0.0
    coinsurance: float = 0.8
    annual_limit: float | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PolicyMeta":
        deductible = _parse_meta_deductible(raw)
        coinsurance = _safe_float(raw.get("coinsurance"), 0.8)
        return cls(
            policy_id=str(raw.get("policy_id", "")),
            policy_name=str(raw.get("policy_name", "")),
            currency=str(raw.get("currency", "USD")),
            deductible=deductible,
            coinsurance=coinsurance,
            annual_limit=to_optional_float(raw.get("annual_limit")),
        )


@dataclass
class Policy:
    meta: PolicyMeta
    coverage_categories: list[CoverageCategory]
    exclusions: list[Exclusion]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Policy":
        policy_raw = raw.get("policy", raw)
        meta = PolicyMeta.from_dict(policy_raw.get("meta", {}))
        categories = [
            CoverageCategory.from_dict(x, fallback_rate=meta.coinsurance)
            for x in policy_raw.get("coverage_categories", [])
        ]
        exclusions = [Exclusion.from_dict(x) for x in policy_raw.get("exclusions", [])]
        return cls(meta=meta, coverage_categories=categories, exclusions=exclusions)


@dataclass
class InvoiceMeta:
    date: str = ""
    hospital_name: str = ""
    diagnosis: str = ""
    visit_reason: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "InvoiceMeta":
        return cls(
            date=str(raw.get("date", "")),
            hospital_name=str(raw.get("hospital_name", "")),
            diagnosis=str(raw.get("diagnosis", "")),
            visit_reason=str(raw.get("visit_reason", "")),
        )


@dataclass
class LineItem:
    id: str
    item_name: str
    item_code: str = ""
    category_hint: str = ""
    quantity: float = 1.0
    unit_cost: float = 0.0
    total_cost: float = 0.0

    @classmethod
    def from_dict(cls, raw: dict[str, Any], index: int) -> "LineItem":
        return cls(
            id=str(raw.get("id", f"line_{index + 1}")),
            item_name=str(raw.get("item_name", "")),
            item_code=str(raw.get("item_code", "")),
            category_hint=str(raw.get("category_hint", "")),
            quantity=float(raw.get("quantity", 1.0)),
            unit_cost=float(raw.get("unit_cost", 0.0)),
            total_cost=float(raw.get("total_cost", 0.0)),
        )


@dataclass
class Bill:
    invoice_meta: InvoiceMeta
    line_items: list[LineItem]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Bill":
        line_items = [
            LineItem.from_dict(x, index=i)
            for i, x in enumerate(raw.get("line_items", []))
        ]
        return cls(
            invoice_meta=InvoiceMeta.from_dict(raw.get("invoice_meta", {})),
            line_items=line_items,
        )


@dataclass
class AppliedClause:
    id: str
    snippet: str = ""


@dataclass
class LineAuditResult:
    line_id: str
    item_name: str
    matched_policy_category_id: str | None
    status: AuditStatus
    allowed_amount: float
    patient_responsible_amount: float
    flags: list[str] = field(default_factory=list)
    applied_clauses: list[AppliedClause] = field(default_factory=list)
    reason: str = ""
    line_total_cost: float = 0.0


@dataclass
class AuditSummary:
    total_invoice_amount: float
    total_approved: float
    total_patient_responsible: float
    currency: str = "USD"
    notes: str = ""


@dataclass
class CategoryUtilizationScore:
    category_id: str
    category_name: str
    premium_score: float
    coverage_score: float
    utilization_score: float
    category_total_score: float
    total_billed: float
    total_approved: float
    line_count: int
    recommendation: str


@dataclass
class UpgradeRecommendation:
    category_id: str
    category_name: str
    additional_cost: float
    estimated_additional_payout: float
    worth_it: bool
    recommendation: str


@dataclass
class UtilizationReport:
    category_scores: list[CategoryUtilizationScore] = field(default_factory=list)
    overall_utilization_score: float = 0.0
    overall_recommendation: str = ""
    upgrade_recommendations: list[UpgradeRecommendation] = field(default_factory=list)


@dataclass
class PolicyOptionScore:
    policy_id: str
    policy_name: str
    price_score: float
    utilization_score: float
    coverage_score: float
    comparison_score: float
    weighted_total_score: float
    total_invoice_amount: float
    total_approved: float
    total_patient_responsible: float
    recommendation: str


@dataclass
class PolicyComparisonReport:
    weights: dict[str, float] = field(default_factory=dict)
    options: list[PolicyOptionScore] = field(default_factory=list)
    best_policy_id: str = ""
    best_policy_name: str = ""
    general_recommendation: str = ""
    user_preference: PolicyPreference | None = None
    preference_best_policy_id: str = ""
    preference_best_policy_name: str = ""
    preference_recommendation: str = ""
    recommendation: str = ""  # Backward-compatible alias of general_recommendation


@dataclass
class AuditResult:
    line_results: list[LineAuditResult]
    summary: AuditSummary
    utilization_report: UtilizationReport | None = None
    policy_comparison_report: PolicyComparisonReport | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditorAgentEntity(BaseAgentEntity):
    currency: str = "USD"
    low_match_confidence_threshold: float = 0.5
    duplicate_handling: DuplicateHandling = "warning"
    strict_currency_check: bool = True
    matcher_name: str = "KeywordSemanticMatcher"
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key_env: str = "OPENAI_API_KEY"
    llm_timeout_seconds: int = 20
    llm_temperature: float = 0.0
    last_summary: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build_default(cls) -> "AuditorAgentEntity":
        return cls(
            agent_id="auditor-agent-c",
            agent_name="Auditor Agent",
            version="v1",
            description=(
                "Cross-checks policy and bill data, then returns per-line payout "
                "decisions with status, amounts, and clause-grounded reasons."
            ),
            input_contract={
                "policy_json": {
                    "legacy_supported": "meta + coverage_categories + exclusions",
                    "new_supported": (
                        "policy.meta + policy.coverage_categories "
                        "(core_clauses accepted) + policy.exclusions (string list accepted)"
                    ),
                },
                "bill_json": {
                    "invoice_meta": "diagnosis, date, hospital_name",
                    "line_items": "id, item_name, item_code, quantity, unit_cost, total_cost",
                },
                "similar_policy_vectors": (
                    "optional list of vector references for B1/C1/D1..., "
                    "resolved by DB/vector integration"
                ),
                "user_preference": "optional: 'price' or 'coverage'",
            },
            output_contract={
                "line_results": "status, allowed_amount, patient_responsible_amount, reason, flags",
                "summary": "total_invoice_amount, total_approved, total_patient_responsible, currency",
                "utilization_report": "category_scores, overall_utilization_score, upgrade_recommendations",
                "policy_comparison_report": (
                    "weighted policy ranking (general) + optional preference-based "
                    "best policy for 'price' or 'coverage'"
                ),
            },
        )


def _parse_coverage_rate(rate: Any, fallback_rate: float) -> float:
    if rate is None:
        return fallback_rate
    if isinstance(rate, (int, float)):
        raw = float(rate)
        if raw > 1:
            if raw <= 100:
                return raw / 100.0
            return 1.0
        return max(0.0, raw)
    if isinstance(rate, dict):
        # Structured text-like rates (for example weekly indemnity) are not directly
        # convertible into payout percentage, so we keep fallback.
        return fallback_rate
    text = str(rate).strip().lower()
    if not text:
        return fallback_rate
    number = to_optional_float(text)
    if number is None:
        return fallback_rate
    if "%" in text:
        return max(0.0, min(1.0, number / 100.0))
    if number > 1:
        if number <= 100:
            return number / 100.0
        return 1.0
    return max(0.0, number)


def _parse_clause_list(raw_clauses: Any) -> list[Clause]:
    clauses: list[Clause] = []
    if not isinstance(raw_clauses, list):
        return clauses
    for index, item in enumerate(raw_clauses):
        if isinstance(item, dict):
            clauses.append(Clause.from_dict(item))
            continue
        text = str(item).strip()
        if not text:
            continue
        clauses.append(Clause(id=f"clause_{index + 1}", text=text))
    return clauses


def _slugify(value: str) -> str:
    lowered = value.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "_", lowered)
    compact = re.sub(r"_+", "_", normalized).strip("_")
    return compact or "unknown"


def _safe_float(value: Any, default: float) -> float:
    parsed = to_optional_float(value)
    return parsed if parsed is not None else default


def _parse_meta_deductible(meta_raw: dict[str, Any]) -> float:
    direct = to_optional_float(meta_raw.get("deductible"))
    if direct is not None:
        return max(0.0, direct)

    deductibles = meta_raw.get("deductibles")
    if isinstance(deductibles, dict):
        numeric_values: list[float] = []
        for val in deductibles.values():
            parsed = to_optional_float(val)
            if parsed is not None:
                numeric_values.append(parsed)
        if numeric_values:
            # Conservative default for mixed deductible declarations.
            return max(0.0, min(numeric_values))
    return 0.0
