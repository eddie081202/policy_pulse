from __future__ import annotations

from typing import Any

from auditor.entities.base_agent_entity import BaseAgentEntity


class BaseAgentService:
    def __init__(self, entity: BaseAgentEntity) -> None:
        self.entity = entity

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Subclasses must implement execute()")
