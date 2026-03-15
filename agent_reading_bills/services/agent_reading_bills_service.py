from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any, Literal

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from pypdf import PdfReader

from ..entities.agent_reading_bills_entity import AgentReadingBillsEntity
from .base_service import BaseService


# ---------------------------------------------------------------------------
# Extraction constants
# ---------------------------------------------------------------------------

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}

_IMAGE_MIME: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
}

# ---------------------------------------------------------------------------
# Transformer constants
# ---------------------------------------------------------------------------

_JSON_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)

# ---------------------------------------------------------------------------
# Sanitizer constants
# ---------------------------------------------------------------------------

_FORBIDDEN_KEYS = {
    "name",
    "full_name",
    "first_name",
    "last_name",
    "middle_name",
    "address",
    "street",
    "city",
    "state",
    "zip",
    "postal_code",
    "phone",
    "email",
    "dob",
    "date_of_birth",
    "ssn",
    "passport",
    "tax_id",
    "member_id",
    "policy_id",
    "policy_number",
}

_EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_PATTERN = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}")
_SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

class DocumentReadResult(BaseModel):
    file_name: str
    file_type: Literal["pdf", "image"]
    document_type: Literal["bill", "contract"]
    extracted_fields: dict
    validation_warnings: list[str]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class AgentReadingBillsService(BaseService):
    def __init__(self, entity: AgentReadingBillsEntity):
        super().__init__(entity)
        self._llm_cache: dict[str, ChatGoogleGenerativeAI] = {}

    # ------------------------------------------------------------------
    # Client
    # ------------------------------------------------------------------

    def _get_llm(self, model_name: str) -> ChatGoogleGenerativeAI:
        if model_name not in self._llm_cache:
            self._llm_cache[model_name] = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=0,
                google_api_key=self.entity.api_key,
            )
        return self._llm_cache[model_name]

    def _response_text(self, response: Any) -> str:
        content = getattr(response, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            return "\n".join(p for p in parts if p).strip()
        return str(content).strip()

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def _normalize_text(self, text: str) -> str:
        lines = [line.rstrip() for line in text.splitlines()]
        return "\n".join(lines).strip()

    def _extract_pdf_text(self, file_path: Path) -> str:
        reader = PdfReader(str(file_path))
        chunks: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text:
                chunks.append(page_text)
        return self._normalize_text("\n\n".join(chunks))

    def _extract_image_text(self, file_path: Path) -> str:
        mime = _IMAGE_MIME[file_path.suffix.lower()]
        b64 = base64.b64encode(file_path.read_bytes()).decode("utf-8")
        llm = self._get_llm(self.entity.vision_model_name)
        response = llm.invoke(
            [
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": "Extract all visible text from this document image exactly as written.",
                        },
                        {
                            "type": "image_url",
                            "image_url": f"data:{mime};base64,{b64}",
                        },
                    ]
                )
            ]
        )
        return self._normalize_text(self._response_text(response))

    def extract_text(self, file_path: str) -> tuple[str, str]:
        """Extract raw text from a PDF or image file.

        Returns:
            Tuple of (text, file_type) where file_type is 'pdf' or 'image'.
        """
        source = Path(file_path)
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(f"Input file not found: {source}")

        suffix = source.suffix.lower()
        if suffix == ".pdf":
            return self._extract_pdf_text(source), "pdf"
        if suffix in _IMAGE_EXTENSIONS:
            return self._extract_image_text(source), "image"
        raise ValueError(
            f"Unsupported file type '{suffix}'. Use .pdf, .png, .jpg, .jpeg, .bmp, .gif, .tif, .tiff, or .webp"
        )

    # ------------------------------------------------------------------
    # Structuring
    # ------------------------------------------------------------------

    def _clean_model_json(self, raw: str) -> str:
        return _JSON_FENCE_PATTERN.sub("", raw).strip()

    def _parse_json_payload(self, raw: str) -> dict[str, Any]:
        cleaned = self._clean_model_json(raw)
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise ValueError("API response is not a JSON object.")
        return data

    def structure_document(self, text: str, document_type: str | None = None) -> dict:
        """Convert extracted text into a PII-filtered structured JSON dict."""
        target_document_type = document_type or self.entity.document_type
        system_prompt = (
            "You are a strict document-to-JSON converter. "
            "Always return valid JSON object only. "
            "During conversion, remove disallowed personal information. "
            "Documents you will be processing are bills or insurance contracts or both. "
            "For each JSON object, only include it in output if it's relevant to billing or insurance policy details. "
            "Consolidate all relevant billing and insurance policy details into the output JSON. "
            "Remove duplicate information and irrelevant details. "
        )

        user_prompt = f"""
Document type: {target_document_type}

Task:
1) Analyze the document and extract critical billing and policy-relevant information, balancing comprehensive coverage details with structural simplicity.
2) Convert the extracted data into a structured JSON format.
3) Summarize verbose legal definitions into concise clauses, but retain exact financial numbers (limits, coverage rates, deductibles) and core conditions.
4) In the same response generation step, absolutely remove all disallowed PII.

Target JSON Structure Guidelines (Adapt based on document type):
- For Policies: Include a `meta` section (currency, deductibles, coinsurance), a `coverage_categories` array (each with name, description, coverage_rate, limits, and brief core clauses), and an `exclusions` array.
- For Bills: Include an `invoice_meta` section (dates, diagnosis, facility/provider info) and a `line_items` array (item_name, quantity, unit_cost, total_cost).

Disallowed PII (must be excluded/anonymized):
- Any patient, insured, or personal contact names (Note: Medical facility or insurance company names are allowed)
- Address details
- Phone numbers and email addresses
- Date of birth
- Government IDs (SSN, passport, tax ID)
- Member IDs and policy IDs/policy numbers
- Any non-financial personal details

Allowed categories:
- Financials: Charges, totals, taxes, line items, due dates, billing period
- Policy Terms: Coverage categories, premium amounts, deductibles, copays, coinsurance, per-item limits, specific exclusions
- Clinical/Service: Service dates, diagnosis names/codes, claim totals, payment status

Output rules:
- Return one valid JSON object only.
- No explanation, preamble, or conversational text.
- Do NOT wrap the output in markdown code blocks.

Document text:
{text}
"""

        llm = self._get_llm(self.entity.llm_model_name)
        response = llm.invoke(
            [
                HumanMessage(
                    content=(
                        f"{system_prompt}\n\n"
                        "Return ONLY one valid JSON object with no markdown wrappers.\n\n"
                        f"{user_prompt}"
                    )
                )
            ]
        )
        content = self._response_text(response) or "{}"
        return self._parse_json_payload(content)

    # ------------------------------------------------------------------
    # PII validation
    # ------------------------------------------------------------------

    def _scan_object(self, obj: Any, parent_key: str = "") -> list[str]:
        warnings: list[str] = []

        if isinstance(obj, dict):
            for key, value in obj.items():
                key_name = str(key).strip().lower()
                if key_name in _FORBIDDEN_KEYS:
                    key_path = f"{parent_key}.{key}" if parent_key else str(key)
                    warnings.append(f"Forbidden key detected: {key_path}")
                child_path = f"{parent_key}.{key}" if parent_key else str(key)
                warnings.extend(self._scan_object(value, child_path))
            return warnings

        if isinstance(obj, list):
            for index, value in enumerate(obj):
                list_path = f"{parent_key}[{index}]" if parent_key else f"[{index}]"
                warnings.extend(self._scan_object(value, list_path))
            return warnings

        value_text = str(obj)
        if _EMAIL_PATTERN.search(value_text):
            warnings.append(f"Possible email found at {parent_key or 'root'}")
        if _PHONE_PATTERN.search(value_text):
            warnings.append(f"Possible phone found at {parent_key or 'root'}")
        if _SSN_PATTERN.search(value_text):
            warnings.append(f"Possible SSN found at {parent_key or 'root'}")

        return warnings

    def _validate(self, structured_dict: dict) -> list[str]:
        return self._scan_object(structured_dict)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def read_document(self, file_path: str, document_type: Literal["bill", "contract"]) -> DocumentReadResult:
        """Extract, structure, and validate a bill or contract document.

        Args:
            file_path: Absolute (or relative) path to the input file.
            document_type: One of 'bill' or 'contract'.

        Returns:
            DocumentReadResult with structured fields and any PII validation warnings.
        """
        text, file_type = self.extract_text(file_path)
        extracted_fields = self.structure_document(text, document_type=document_type)
        validation_warnings = self._validate(extracted_fields)
        return DocumentReadResult(
            file_name=Path(file_path).name,
            file_type=file_type,
            document_type=document_type,
            extracted_fields=extracted_fields,
            validation_warnings=validation_warnings,
        )

    def read_bill(self, file_path: str) -> DocumentReadResult:
        """Backward-compatible convenience wrapper for bill documents."""
        return self.read_document(file_path, document_type="bill")

    def read_contract(self, file_path: str) -> DocumentReadResult:
        """Read a contract document and output bill-like filtered JSON."""
        return self.read_document(file_path, document_type="contract")
