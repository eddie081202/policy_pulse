from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
