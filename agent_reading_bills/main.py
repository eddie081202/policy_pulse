from .entities import AgentReadingBillsEntity
from .services import AgentReadingBillsService, DocumentReadResult

_entity = AgentReadingBillsEntity()
_service = AgentReadingBillsService(_entity)


def read_bill(file_path: str) -> DocumentReadResult:
    """Extract and structure a bill document (PDF or image) into filtered JSON.

    Args:
        file_path: Path to the bill file (.pdf, .png, .jpg, etc.)

    Returns:
        DocumentReadResult with extracted_fields dict and any PII validation_warnings.
    """
    return _service.read_bill(file_path)


def read_contract(file_path: str) -> DocumentReadResult:
    """Extract and structure a contract document (PDF or image) into filtered JSON.

    Args:
        file_path: Path to the contract file (.pdf, .png, .jpg, etc.)

    Returns:
        DocumentReadResult with extracted_fields dict and any PII validation_warnings.
    """
    return _service.read_contract(file_path)
