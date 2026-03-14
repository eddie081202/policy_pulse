from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from auditor.entities.base_entity import to_optional_float


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
            per_item_limit=to_optional_float(raw.get("per_item_limit")),
            per_day_limit=to_optional_float(raw.get("per_day_limit")),
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
            annual_limit=to_optional_float(raw.get("annual_limit")),
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
