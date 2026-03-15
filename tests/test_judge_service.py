from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agent_auditor.main import evaluate_payload


def test_judge_service_returns_contract_shape():
    parser_payload = {
        "bill_payload": {
            "file_name": "bill.png",
            "extracted_fields": {
                "line_items": [
                    {"item_name": "Primary Care Visit"},
                    {"item_name": "Emergency Room Service"},
                ]
            },
            "validation_warnings": [],
        },
        "contract_payload": {
            "file_name": "contract.pdf",
            "extracted_fields": {
                "meta": {
                    "policy_number": "CURRENT-1",
                    "premium_monthly": 500.0,
                    "individual_deductible": 1200.0,
                },
                "coverage_categories": [
                    {"name": "Primary Care"},
                    {"name": "Emergency Room"},
                ],
            },
            "validation_warnings": [],
        },
    }
    rag_payload = {
        "confidence": 0.72,
        "matched_candidates": [
            {
                "policy_id": "ALT-1",
                "policy_name": "Alternative 1",
                "category": "health",
                "premium_monthly": 420.0,
                "deductible_individual": 1000.0,
                "coverage_keywords": ["primary care", "emergency room", "prescription"],
                "source_references": [
                    {"source_file": "alt1.pdf", "source_path": "/tmp/alt1.pdf", "chunk_id": "1"}
                ],
            }
        ],
        "matched_documents": [],
        "discrepancies": [],
    }

    result = evaluate_payload(parser_payload, rag_payload, preference="price").model_dump()

    assert "request_id" in result
    assert result["preference"] == "price"
    assert "current_policy" in result
    assert "total_score" in result
    assert "alternatives" in result
    assert "recommendation" in result
    assert "weights" in result

