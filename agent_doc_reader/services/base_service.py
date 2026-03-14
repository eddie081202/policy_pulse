from ..entities.base_entity import BaseEntity


class BaseService:
    def __init__(self, entity: BaseEntity):
        self.entity = entity

    def query(self, question: str) -> str:
        raise NotImplementedError("Subclasses must implement query()")
