from .entities.agent_doc_reader_entity import AgentDocReaderEntity
from .services.agent_doc_reader_service import AgentDocReaderService

_entity = AgentDocReaderEntity()
_service = AgentDocReaderService(_entity)

def query_csv_contracts(question: str) -> str:
    """Query the insurance contracts vector store and return a natural language answer."""
    return _service.query(question)
