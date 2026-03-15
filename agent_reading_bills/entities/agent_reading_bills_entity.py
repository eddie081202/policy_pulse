from pathlib import Path

from .base_entity import BaseEntity

_ROOT = Path(__file__).parent.parent.parent


class AgentReadingBillsEntity(BaseEntity):
    def __init__(
        self,
        llm_model_name: str = "gpt-4.1-mini",
        vision_model_name: str = "gpt-4.1-mini",
        api_key: str = None,
        document_type: str = "bill",
        csv_path: str = None,
    ):
        super().__init__(
            llm_model_name=llm_model_name,
            vision_model_name=vision_model_name,
            api_key=api_key,
        )
        self.document_type = document_type
        self.csv_path = csv_path or str(
            _ROOT / "bills" / "insurance_bills" / "insurance_bills_100.csv"
        )
