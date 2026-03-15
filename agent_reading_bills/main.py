from pathlib import Path

from .entities import AgentReadingBillsEntity
from .services import AgentReadingBillsService, DocumentReadResult

_entity = AgentReadingBillsEntity()
_service = AgentReadingBillsService(_entity)


def read_bill(file_path: str) -> DocumentReadResult:
    """Extract and structure a bill document (PDF or image) into filtered JSON."""
    return _service.read_bill(file_path)


def read_contract(file_path: str) -> DocumentReadResult:
    """Extract and structure a contract document (PDF or image) into filtered JSON."""
    return _service.read_contract(file_path)


def build_user_payload(bill_path: str | Path, contract_path: str | Path) -> dict:
    """Build a single downstream JSON object from bill and contract inputs."""
    bill_path = Path(bill_path)
    contract_path = Path(contract_path)

    if not bill_path.exists() or not bill_path.is_file():
        raise FileNotFoundError(f"Bill file not found: {bill_path}")
    if not contract_path.exists() or not contract_path.is_file():
        raise FileNotFoundError(f"Contract file not found: {contract_path}")

    bill_payload = read_bill(str(bill_path)).model_dump()
    contract_payload = read_contract(str(contract_path)).model_dump()

    return {
        "bill_payload": bill_payload,
        "contract_payload": contract_payload,
    }