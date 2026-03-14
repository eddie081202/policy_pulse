from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from auditor.entities.base_agent_entity import BaseAgentEntity


class BaseAgentService(ABC):
    def __init__(self, entity: BaseAgentEntity) -> None:
        self.entity = entity

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError
