from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


AuditStatus = Literal["approved", "rejected", "partial", "warning"]


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
    scope: str = "all_conditions"
    clauses: list[Clause] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any], fallback_rate: float) -> "CoverageCategory":
        rate = raw.get("coverage_rate")
        category_rate = float(rate) if rate is not None else float(fallback_rate)
        return cls(
            id=str(raw.get("id", "")),
            name=str(raw.get("name", "")),
            description=str(raw.get("description", "")),
            coverage_rate=category_rate,
            per_item_limit=_to_optional_float(raw.get("per_item_limit")),
            per_day_limit=_to_optional_float(raw.get("per_day_limit")),
            scope=str(raw.get("scope", "all_conditions")),
            clauses=[Clause.from_dict(x) for x in raw.get("clauses", [])],
        )


@dataclass
class Exclusion:
    id: str
    name: str
    text: str = ""
    clauses: list[Clause] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Exclusion":
        return cls(
            id=str(raw.get("id", "")),
            name=str(raw.get("name", "")),
            text=str(raw.get("text", "")),
            clauses=[Clause.from_dict(x) for x in raw.get("clauses", [])],
        )


@dataclass
class PolicyMeta:
    currency: str = "USD"
    deductible: float = 0.0
    coinsurance: float = 0.8
    annual_limit: float | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PolicyMeta":
        return cls(
            currency=str(raw.get("currency", "USD")),
            deductible=float(raw.get("deductible", 0.0)),
            coinsurance=float(raw.get("coinsurance", 0.8)),
            annual_limit=_to_optional_float(raw.get("annual_limit")),
        )


@dataclass
class Policy:
    meta: PolicyMeta
    coverage_categories: list[CoverageCategory]
    exclusions: list[Exclusion]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Policy":
        meta = PolicyMeta.from_dict(raw.get("meta", {}))
        categories = [
            CoverageCategory.from_dict(x, fallback_rate=meta.coinsurance)
            for x in raw.get("coverage_categories", [])
        ]
        exclusions = [Exclusion.from_dict(x) for x in raw.get("exclusions", [])]
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
class AuditResult:
    line_results: list[LineAuditResult]
    summary: AuditSummary

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _to_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
