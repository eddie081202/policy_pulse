from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from agent_doc_reader.main import audit_document
from agent_reading_bills.main import build_user_payload
from judge.main import evaluate_payload

router = APIRouter(prefix="/api/judge", tags=["judge"])

PreferenceMode = Literal["price", "policy", "no_preference"]
_ALLOWED_BILL_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp", ".pdf"}
_ALLOWED_CONTRACT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp", ".pdf"}


def _save_upload(temp_dir: Path, upload: UploadFile) -> Path:
    if not upload.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must include a filename.")
    file_path = temp_dir / upload.filename
    with file_path.open("wb") as destination:
        shutil.copyfileobj(upload.file, destination)
    return file_path


def _validate_upload(upload: UploadFile, allowed_extensions: set[str], file_label: str) -> None:
    filename = upload.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"{file_label} must be one of: {', '.join(sorted(allowed_extensions))}",
        )


@router.post("/evaluate")
async def evaluate_judge(
    bill_file: UploadFile = File(...),
    contract_file: UploadFile = File(...),
    preference: PreferenceMode = Form("no_preference"),
):
    if preference not in {"price", "policy", "no_preference"}:
        raise HTTPException(status_code=400, detail="preference must be one of: price, policy, no_preference")
    _validate_upload(bill_file, _ALLOWED_BILL_EXTENSIONS, "bill_file")
    _validate_upload(contract_file, _ALLOWED_CONTRACT_EXTENSIONS, "contract_file")

    with tempfile.TemporaryDirectory(prefix="judge_eval_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        bill_path = _save_upload(temp_dir, bill_file)
        contract_path = _save_upload(temp_dir, contract_file)

        try:
            parser_payload = build_user_payload(str(bill_path), str(contract_path))
            rag_payload = audit_document(str(contract_path)).model_dump()
            result = evaluate_payload(parser_payload, rag_payload, preference=preference)
            return result.model_dump()
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # Defensive fallback
            raise HTTPException(status_code=500, detail=f"Judge evaluation failed: {exc}") from exc

