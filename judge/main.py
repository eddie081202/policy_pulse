from __future__ import annotations

from .entities import JudgeEntity
from .services import JudgeInput, JudgeResult, JudgeService

_entity = JudgeEntity()
_service = JudgeService(_entity)


def evaluate_payload(parser_payload: dict, rag_payload: dict, preference: str = "no_preference") -> JudgeResult:
    payload = JudgeInput(
        parser_payload=parser_payload,
        rag_payload=rag_payload,
        preference=preference,  # type: ignore[arg-type]
    )
    return _service.evaluate(payload)

