from .entities import AgentDocReaderEntity
from .services import AgentDocReaderService, AuditResult

# Single entity and service that handles both CSV and PDF
_entity = AgentDocReaderEntity()
_service = AgentDocReaderService(_entity)


def query_contracts(question: str) -> str:
    """Query the unified insurance contracts vectorstore (CSV + PDF) and return a natural language answer."""
    return _service.query_contracts(question)


def audit_document(file_path: str) -> AuditResult:
    """Ingest a user-uploaded contract file (PDF or image) and audit it against existing contracts."""
    return _service.audit_document(file_path)
