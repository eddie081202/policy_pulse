from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any


def run_full_audit_pipeline(
    bill_file_path: str,
    contract_file_path: str,
    user_preference: str | None = None,
    similar_policies_json: list[dict[str, Any]] | None = None,
    similar_policy_vectors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    End-to-end orchestration for:
      1) bill extraction
      2) contract extraction
      3) contract reference retrieval (RAG)
      4) normalization into auditor contracts
      5) final auditor execution

    Returns only the final auditor output JSON.
    Supports optional similar policy comparison inputs.
    """
    from agent_doc_reader import audit_document
    from agent_reading_bills import read_bill, read_contract
    from auditor.main import audit_invoice_from_json

    bill_result = read_bill(bill_file_path)
    contract_result = read_contract(contract_file_path)
    doc_reader_result = audit_document(contract_file_path)

    refs = [ref.model_dump() for ref in doc_reader_result.matched_documents]
    resolved_docs = resolve_document_references(refs)

    bill_json = normalize_bill_payload(bill_result.extracted_fields)
    policy_json = normalize_policy_payload(
        contract_payload=contract_result.extracted_fields,
        resolved_docs=resolved_docs,
    )

    audit_result = audit_invoice_from_json(
        policy_json=policy_json,
        bill_json=bill_json,
        similar_policies_json=similar_policies_json,
        similar_policy_vectors=similar_policy_vectors,
        user_preference=user_preference,
    )
    return audit_result.to_dict()


def resolve_document_references(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Resolve DocumentReference entries by source_path + page/chunk_id.

    For PDFs:
      - Use source_path + page for page-level extraction.
      - Fallback to source_path + chunk_id if chunk_id is an integer-like page index.

    For CSV:
      - Resolve row by 'contract_id' == chunk_id.
      - If chunk_id is integer-like, resolve by row index fallback.
    """
    resolved: list[dict[str, Any]] = []
    for ref in refs:
        resolved_text = ""
        method = "fallback_text"

        source_path = str(ref.get("source_path", "") or "")
        source_file = str(ref.get("source_file", "") or "")
        chunk_id = str(ref.get("chunk_id", "") or "")
        page = ref.get("page")
        category = ref.get("category")
        original_text = str(ref.get("text", "") or "")
        score = ref.get("score")

        if source_path:
            path = Path(source_path)
            if path.exists() and path.is_file():
                suffix = path.suffix.lower()
                if suffix == ".pdf":
                    resolved_text, method = _resolve_pdf_text(path, page=page, chunk_id=chunk_id)
                elif suffix == ".csv":
                    resolved_text, method = _resolve_csv_text(path, chunk_id=chunk_id)

        if not resolved_text:
            resolved_text = original_text

        resolved.append(
            {
                "chunk_id": chunk_id,
                "source_file": source_file,
                "source_path": source_path,
                "category": category,
                "page": page,
                "score": score,
                "text": original_text,
                "resolved_text": resolved_text,
                "resolution_method": method,
            }
        )
    return resolved


def normalize_bill_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a potentially nondeterministic bill payload into auditor bill schema.
    """
    invoice_meta_source = _first_dict(raw, ["invoice_meta", "meta", "bill_meta", "header"])
    invoice_meta = {
        "date": _first_str(invoice_meta_source or raw, ["date", "service_date", "invoice_date"]),
        "hospital_name": _first_str(
            invoice_meta_source or raw,
            ["hospital_name", "provider_name", "facility_name", "clinic_name"],
        ),
        "diagnosis": _first_str(invoice_meta_source or raw, ["diagnosis", "diagnosis_name", "icd_desc"]),
        "visit_reason": _first_str(invoice_meta_source or raw, ["visit_reason", "reason", "chief_complaint"]),
    }

    candidate_line_items = _first_list(
        raw,
        [
            "line_items",
            "items",
            "charges",
            "service_lines",
            "services",
            "bill_items",
        ],
    )

    line_items: list[dict[str, Any]] = []
    for idx, item in enumerate(candidate_line_items):
        if not isinstance(item, dict):
            continue

        item_name = _first_str(
            item,
            ["item_name", "name", "description", "service", "procedure", "title"],
        )
        quantity = _first_float(item, ["quantity", "qty", "count"], default=1.0)
        unit_cost = _first_float(item, ["unit_cost", "unit_price", "price", "rate"], default=0.0)
        total_cost = _first_float(
            item,
            ["total_cost", "line_total", "amount", "cost", "charge", "billed_amount"],
            default=round(quantity * unit_cost, 2),
        )
        item_code = _first_str(item, ["item_code", "code", "cpt_code", "hcpcs_code"])
        category_hint = _first_str(item, ["category_hint", "category", "type", "service_type"])

        if not item_name:
            continue

        line_items.append(
            {
                "id": _first_str(item, ["id", "line_id"]) or f"line_{idx + 1}",
                "item_name": item_name,
                "item_code": item_code,
                "category_hint": category_hint,
                "quantity": max(0.0, quantity),
                "unit_cost": max(0.0, unit_cost),
                "total_cost": max(0.0, total_cost),
            }
        )

    if not line_items:
        fallback_total = _first_float(
            raw,
            ["total_amount", "amount_due", "bill_total", "invoice_total"],
            default=0.0,
        )
        line_items = [
            {
                "id": "line_1",
                "item_name": "General Medical Service",
                "item_code": "",
                "category_hint": "",
                "quantity": 1.0,
                "unit_cost": round(max(0.0, fallback_total), 2),
                "total_cost": round(max(0.0, fallback_total), 2),
            }
        ]

    return {
        "invoice_meta": invoice_meta,
        "line_items": line_items,
    }


def normalize_policy_payload(
    contract_payload: dict[str, Any],
    resolved_docs: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Convert potentially nondeterministic contract payload into auditor policy schema.
    """
    policy_root = _first_dict(contract_payload, ["policy"]) or contract_payload
    meta_source = _first_dict(policy_root, ["meta", "policy_meta", "header"]) or policy_root

    policy_id = _first_str(meta_source, ["policy_id", "id", "contract_id", "plan_id"]) or "A1"
    policy_name = _first_str(meta_source, ["policy_name", "name", "plan_name", "contract_name"]) or "User Policy"
    deductible = _first_float(meta_source, ["deductible"], default=0.0)
    coinsurance = _first_rate(meta_source, ["coinsurance", "coverage_rate"], default=0.8)

    coverage_raw = _first_list(
        policy_root,
        ["coverage_categories", "coverages", "benefits", "categories", "plans"],
    )
    coverage_categories = _normalize_coverage_categories(coverage_raw, fallback_coinsurance=coinsurance)
    if not coverage_categories:
        coverage_categories = _coverage_from_resolved_docs(resolved_docs, fallback_coinsurance=coinsurance)
    if not coverage_categories:
        coverage_categories = [
            {
                "id": "general_coverage",
                "name": "General Coverage",
                "description": "Fallback category synthesized from contract extraction.",
                "coverage_rate": coinsurance,
                "scope": "all_conditions",
                "core_clauses": ["General medical services covered based on policy coinsurance."],
            }
        ]

    exclusions_raw = _first_list(policy_root, ["exclusions", "not_covered", "excluded_services"])
    exclusions = _normalize_exclusions(exclusions_raw)

    return {
        "policy": {
            "meta": {
                "policy_id": policy_id,
                "policy_name": policy_name,
                "currency": "USD",
                "deductible": max(0.0, deductible),
                "coinsurance": _clamp(coinsurance, 0.0, 1.0),
            },
            "coverage_categories": coverage_categories,
            "exclusions": exclusions,
        }
    }


def _resolve_pdf_text(path: Path, page: Any, chunk_id: str) -> tuple[str, str]:
    try:
        from pypdf import PdfReader
    except Exception:
        return "", "pypdf_unavailable"

    try:
        reader = PdfReader(str(path))
    except Exception:
        return "", "pdf_open_failed"

    page_index = _to_int(page)
    if page_index is not None and 0 <= page_index < len(reader.pages):
        text = (reader.pages[page_index].extract_text() or "").strip()
        if text:
            return text, "pdf_page"

    chunk_index = _to_int(chunk_id)
    if chunk_index is not None and 0 <= chunk_index < len(reader.pages):
        text = (reader.pages[chunk_index].extract_text() or "").strip()
        if text:
            return text, "pdf_chunk_as_page"

    return "", "pdf_unresolved"


def _resolve_csv_text(path: Path, chunk_id: str) -> tuple[str, str]:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception:
        return "", "csv_open_failed"

    if not rows:
        return "", "csv_empty"

    if chunk_id:
        for row in rows:
            if str(row.get("contract_id", "")).strip() == chunk_id:
                return _row_to_text(row), "csv_contract_id"

        idx = _to_int(chunk_id)
        if idx is not None and 0 <= idx < len(rows):
            return _row_to_text(rows[idx]), "csv_row_index"

    return "", "csv_unresolved"


def _row_to_text(row: dict[str, Any]) -> str:
    parts = []
    for key, value in row.items():
        value_text = str(value).strip()
        if not value_text:
            continue
        label = key.replace("_", " ").title()
        parts.append(f"{label}: {value_text}")
    return ". ".join(parts).strip()


def _normalize_coverage_categories(
    categories: list[Any],
    fallback_coinsurance: float,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for idx, category in enumerate(categories):
        if not isinstance(category, dict):
            continue

        name = _first_str(category, ["name", "category", "title", "type"])
        if not name:
            name = f"Coverage Category {idx + 1}"

        coverage_rate = _first_rate(
            category,
            ["coverage_rate", "rate", "coinsurance", "coverage_percentage", "percent"],
            default=fallback_coinsurance,
        )

        limits = _first_dict(category, ["limits"]) or {}
        per_item_limit = _first_float(
            limits if limits else category,
            ["per_item", "per_item_limit", "item_limit"],
            default=0.0,
        )
        per_day_limit = _first_float(
            limits if limits else category,
            ["per_day", "per_day_limit", "daily_limit"],
            default=0.0,
        )

        scope = _first_str(category, ["scope", "condition_scope"]) or "all_conditions"
        clauses = _normalize_clauses(category)

        category_json: dict[str, Any] = {
            "id": _first_str(category, ["id"]) or _slugify(name),
            "name": name,
            "description": _first_str(category, ["description", "summary", "details"]),
            "coverage_rate": _clamp(coverage_rate, 0.0, 1.0),
            "scope": scope,
            "core_clauses": clauses,
        }

        premium_score = _first_float(category, ["premium_score"], default=-1.0)
        if premium_score >= 0:
            category_json["premium_score"] = _clamp(premium_score, 0.0, 100.0)

        upgrade_premium_cost = _first_float(category, ["upgrade_premium_cost"], default=-1.0)
        if upgrade_premium_cost >= 0:
            category_json["upgrade_premium_cost"] = max(0.0, upgrade_premium_cost)

        upgrade_coverage_rate = _first_rate(category, ["upgrade_coverage_rate"], default=-1.0)
        if upgrade_coverage_rate >= 0:
            category_json["upgrade_coverage_rate"] = _clamp(upgrade_coverage_rate, 0.0, 1.0)

        if per_item_limit > 0:
            category_json.setdefault("limits", {})["per_item"] = per_item_limit
        if per_day_limit > 0:
            category_json.setdefault("limits", {})["per_day"] = per_day_limit

        normalized.append(category_json)

    return normalized


def _coverage_from_resolved_docs(
    resolved_docs: list[dict[str, Any]],
    fallback_coinsurance: float,
) -> list[dict[str, Any]]:
    by_category: dict[str, list[str]] = {}
    for doc in resolved_docs:
        category = str(doc.get("category") or "").strip() or "general"
        text = str(doc.get("resolved_text") or doc.get("text") or "").strip()
        if not text:
            continue
        by_category.setdefault(category, []).append(text[:300])

    normalized: list[dict[str, Any]] = []
    for category, snippets in by_category.items():
        label = category.replace("_", " ").title()
        normalized.append(
            {
                "id": _slugify(category),
                "name": label,
                "description": f"Synthesized from retrieved {label} contract references.",
                "coverage_rate": _clamp(fallback_coinsurance, 0.0, 1.0),
                "scope": "all_conditions",
                "core_clauses": snippets[:3] or ["Clause context derived from retrieved documents."],
            }
        )
    return normalized


def _normalize_exclusions(exclusions_raw: list[Any]) -> list[Any]:
    normalized: list[Any] = []
    for idx, entry in enumerate(exclusions_raw):
        if isinstance(entry, str):
            text = entry.strip()
            if text:
                normalized.append(text)
            continue

        if not isinstance(entry, dict):
            continue

        name = _first_str(entry, ["name", "title", "type"]) or f"Exclusion {idx + 1}"
        text = _first_str(entry, ["text", "description", "details"]) or name
        normalized.append(
            {
                "id": _first_str(entry, ["id"]) or _slugify(name),
                "name": name,
                "text": text,
                "clauses": [{"id": f"{_slugify(name)}_clause_1", "text": text}],
            }
        )
    return normalized


def _normalize_clauses(category: dict[str, Any]) -> list[str]:
    for key in ("core_clauses", "clauses", "terms", "conditions"):
        val = category.get(key)
        if isinstance(val, list):
            output: list[str] = []
            for item in val:
                if isinstance(item, str):
                    text = item.strip()
                    if text:
                        output.append(text)
                elif isinstance(item, dict):
                    text = _first_str(item, ["text", "description", "snippet"])
                    if text:
                        output.append(text)
            if output:
                return output

    fallback = _first_str(category, ["description", "summary", "details"])
    if fallback:
        return [fallback]
    return ["Coverage clause details not explicitly provided in source payload."]


def _first_dict(source: dict[str, Any], keys: list[str]) -> dict[str, Any] | None:
    for key in keys:
        val = source.get(key)
        if isinstance(val, dict):
            return val
    return None


def _first_list(source: dict[str, Any], keys: list[str]) -> list[Any]:
    for key in keys:
        val = source.get(key)
        if isinstance(val, list):
            return val
    return []


def _first_str(source: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        if key not in source:
            continue
        val = source.get(key)
        if val is None:
            continue
        if isinstance(val, str):
            stripped = val.strip()
            if stripped:
                return stripped
            continue
        text = str(val).strip()
        if text:
            return text
    return ""


def _first_float(source: dict[str, Any], keys: list[str], default: float) -> float:
    for key in keys:
        if key not in source:
            continue
        parsed = _to_float(source.get(key))
        if parsed is not None:
            return parsed
    return default


def _first_rate(source: dict[str, Any], keys: list[str], default: float) -> float:
    for key in keys:
        if key not in source:
            continue
        parsed = _parse_rate(source.get(key))
        if parsed is not None:
            return parsed
    return default


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if match is None:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _parse_rate(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        raw = float(value)
        if raw > 1.0:
            return raw / 100.0 if raw <= 100.0 else 1.0
        return max(0.0, raw)

    text = str(value).strip().lower()
    if not text:
        return None

    number = _to_float(text)
    if number is None:
        return None
    if "%" in text:
        return number / 100.0
    if number > 1.0:
        return number / 100.0 if number <= 100.0 else 1.0
    return max(0.0, number)


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    return None


def _slugify(value: str) -> str:
    lowered = value.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "_", lowered)
    compact = re.sub(r"_+", "_", normalized).strip("_")
    return compact or "unknown"


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))

