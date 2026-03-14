from .entities import AgentDocReaderEntity
from .services import AgentDocReaderService

# Single entity and service that handles both CSV and PDF
_entity = AgentDocReaderEntity()
_service = AgentDocReaderService(_entity)


def query_csv_contracts(question: str) -> str:
    """Query the insurance contracts CSV vector store and return a natural language answer."""
    return _service.query(question)


def query_pdf_contracts(question: str) -> str:
    """Query the insurance contracts PDF vector store and return a natural language answer."""
    return _service.query_pdf(question)
