from pathlib import Path
import sys

from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.main import app
import backend.routes.judge as judge_route


def run_smoke_test() -> None:
    original_build_user_payload = judge_route.build_user_payload
    original_audit_document = judge_route.audit_document
    original_evaluate_payload = judge_route.evaluate_payload

    def fake_build_user_payload(bill_path: str, contract_path: str) -> dict:
        return {
            "bill_payload": {"file_name": bill_path, "extracted_fields": {"line_items": []}, "validation_warnings": []},
            "contract_payload": {
                "file_name": contract_path,
                "extracted_fields": {"meta": {"premium_monthly": 550.0, "individual_deductible": 1400.0}},
                "validation_warnings": [],
            },
        }

    class _FakeAuditResult:
        def model_dump(self) -> dict:
            return {
                "matched_documents": [],
                "matched_candidates": [
                    {
                        "policy_id": "ALT-1",
                        "policy_name": "Alternative 1",
                        "premium_monthly": 490.0,
                        "deductible_individual": 1200.0,
                        "coverage_keywords": [],
                        "source_references": [
                            {"source_file": "alt1.pdf", "source_path": "alt1.pdf", "chunk_id": "c1"}
                        ],
                    }
                ],
                "confidence": 0.75,
                "discrepancies": [],
            }

    def fake_audit_document(_path: str) -> _FakeAuditResult:
        return _FakeAuditResult()

    def fake_evaluate_payload(parser_payload: dict, rag_payload: dict, preference: str):
        from judge.main import evaluate_payload as real_evaluate_payload

        return real_evaluate_payload(parser_payload, rag_payload, preference=preference)

    judge_route.build_user_payload = fake_build_user_payload
    judge_route.audit_document = fake_audit_document
    judge_route.evaluate_payload = fake_evaluate_payload

    try:
        client = TestClient(app)
        files = {
            "bill_file": ("bill.png", b"sample-bill", "image/png"),
            "contract_file": ("contract.pdf", b"sample-contract", "application/pdf"),
        }
        response = client.post("/api/judge/evaluate", files=files, data={"preference": "no_preference"})
        assert response.status_code == 200, response.text
        payload = response.json()
        assert "current_policy" in payload
        assert "total_score" in payload
        assert "alternatives" in payload
        assert "recommendation" in payload
        assert payload["preference"] == "no_preference"
    finally:
        judge_route.build_user_payload = original_build_user_payload
        judge_route.audit_document = original_audit_document
        judge_route.evaluate_payload = original_evaluate_payload


if __name__ == "__main__":
    run_smoke_test()
    print("smoke_judge_api_contract: ok")

