from pathlib import Path

from .base_entity import BaseEntity

_ROOT = Path(__file__).parent.parent.parent


class AgentDocReaderEntity(BaseEntity):
    def __init__(
        self,
        llm_model_name: str = "gpt-4o",
        embedding_model_name: str = "text-embedding-3-small",
        api_key: str = None,
        csv_path: str = None,
        csv_vectorstore_path: str = None,
        collection_name: str = "insurance_contracts",
        metadata_fields: set = None,
        k: int = 10,
        system_prompt: str = (
            "You are an expert insurance contract analyst. "
            "Use the retrieved contract data below to answer the question accurately and concisely.\n\n"
            "Contract Data:\n{context}\n\n"
            "Question: {question}\n"
            "Answer:"
        ),
    ):
        super().__init__(
            llm_model_name=llm_model_name,
            embedding_model_name=embedding_model_name,
            api_key=api_key,
        )
        self.csv_path = csv_path or str(
            _ROOT / "data" / "insurance_contracts" / "insurance_contracts_10.csv"
        )
        self.csv_vectorstore_path = csv_vectorstore_path or str(
            _ROOT / "data" / "vectorstore" / "csv"
        )
        self.collection_name = collection_name
        self.metadata_fields = metadata_fields or {"contract_id", "contract_type", "policy_number"}
        self.k = k
        self.system_prompt = system_prompt
