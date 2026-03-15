#!/usr/bin/env python3
"""
Run the full Bill Auditor pipeline from two input paths:
1) bill file path
2) insurance contract file path

Pipeline:
- Parser: build_user_payload(...)
- RAG/Audit: audit_document(...)
- Judge: evaluate_payload(...)

Example:
  python run_full_pipeline.py \
    --bill "/Users/eddiehuynh/Main/Hackathon/Bill_auditor/policy_pulse/data/insurance_bills/bill_008_auto_paid.png" \
    --contract "/Users/eddiehuynh/Main/Hackathon/Bill_auditor/policy_pulse/data/insurance_contracts/auto/09_StateFarm_FL_Auto_Policy_9810C.pdf" \
    --preference no_preference
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def _resolve_paths(bill: str, contract: str) -> tuple[Path, Path]:
    bill_path = Path(bill).expanduser().resolve()
    contract_path = Path(contract).expanduser().resolve()

    if not bill_path.exists() or not bill_path.is_file():
        raise FileNotFoundError(f"Bill file not found: {bill_path}")
    if not contract_path.exists() or not contract_path.is_file():
        raise FileNotFoundError(f"Contract file not found: {contract_path}")

    return bill_path, contract_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full Judge pipeline from bill + contract files.")
    parser.add_argument("--bill", required=True, help="Path to bill file (image or pdf)")
    parser.add_argument("--contract", required=True, help="Path to insurance contract file (image or pdf)")
    parser.add_argument(
        "--preference",
        default="no_preference",
        choices=["price", "policy", "no_preference"],
        help="Recommendation preference mode",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional output JSON file path. If omitted, prints to stdout.",
    )
    args = parser.parse_args()

    # If this script is outside policy_pulse, add project root to import path.
    # If script lives inside policy_pulse, this is harmless.
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from agent_reading_bills.main import build_user_payload
    from agent_doc_reader.main import audit_document
    from judge.main import evaluate_payload

    bill_path, contract_path = _resolve_paths(args.bill, args.contract)

    # 1) Parser payload (bill + contract extraction)
    parser_payload = build_user_payload(str(bill_path), str(contract_path))

    # 2) RAG/Audit payload from contract against vectorized knowledge base
    rag_payload = audit_document(str(contract_path)).model_dump()

    # 3) Judge output (final scoring + alternatives + recommendation)
    judge_result = evaluate_payload(
        parser_payload=parser_payload,
        rag_payload=rag_payload,
        preference=args.preference,
    ).model_dump()

    response = {
        "inputs": {
            "bill_path": str(bill_path),
            "contract_path": str(contract_path),
            "preference": args.preference,
        },
        "parser_payload": parser_payload,
        "rag_payload": rag_payload,
        "judge_result": judge_result,
    }

    json_text = json.dumps(response, indent=2, ensure_ascii=True)

    if args.output:
        out_path = Path(args.output).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json_text, encoding="utf-8")
        print(f"Wrote pipeline response to: {out_path}")
    else:
        print(json_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())