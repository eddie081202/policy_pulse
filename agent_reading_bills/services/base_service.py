from ..entities.base_entity import BaseEntity


class BaseService:
    def __init__(self, entity: BaseEntity):
        self.entity = entity

    def extract_text(self, file_path: str) -> tuple[str, str]:
        raise NotImplementedError("Subclasses must implement extract_text()")

    def structure_document(self, text: str, document_type: str | None = None) -> dict:
        raise NotImplementedError("Subclasses must implement structure_document()")
