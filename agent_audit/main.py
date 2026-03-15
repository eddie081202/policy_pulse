from __future__ import annotations

from .entities import AuditorEntity
from .services import AuditorInput, AuditorResult, AuditorService

_entity = AuditorEntity()
_service = AuditorService(_entity)


def evaluate_payload(parser_payload: dict, rag_payload: dict, preference: str = "no_preference") -> AuditorResult:
    payload = AuditorInput(
        parser_payload=parser_payload,
        rag_payload=rag_payload,
        preference=preference,  # type: ignore[arg-type]
    )
    return _service.evaluate(payload)

