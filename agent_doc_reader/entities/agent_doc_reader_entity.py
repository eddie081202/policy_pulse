from pathlib import Path

from .base_entity import BaseEntity

_ROOT = Path(__file__).parent.parent.parent


class AgentDocReaderEntity(BaseEntity):
    def __init__(
        self,
        llm_model_name: str = "gpt-5-mini",
        embedding_model_name: str = "text-embedding-3-small",
        api_key: str = None,
        # CSV configuration
        csv_path: str = None,
        csv_metadata_fields: set = None,
        # PDF configuration
        pdf_dir: str = None,
        pdf_chunks_path: str = None,
        chunk_size: int = 1200,
        chunk_overlap: int = 200,
        # Unified vectorstore
        vectorstore_path: str = None,
        collection_name: str = "insurance_contracts",
        # Shared configuration
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
        # CSV configuration
        self.csv_path = csv_path or str(
            _ROOT / "data" / "insurance_contracts" / "csv" / "insurance_contracts_10.csv"
        )
        self.metadata_fields = csv_metadata_fields or {"contract_id", "contract_type", "policy_number"}

        # PDF configuration
        self.pdf_dir = pdf_dir or str(
            _ROOT / "data" / "insurance_contracts"
        )
        self.pdf_chunks_path = pdf_chunks_path or str(
            _ROOT / "data" / "vectorstore" / "pdf_chunks.jsonl"
        )
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Unified vectorstore
        self.vectorstore_path = vectorstore_path or str(
            _ROOT / "data" / "vectorstore" / "unified"
        )
        self.collection_name = collection_name

        # Shared configuration
        self.k = k
        self.system_prompt = system_prompt

        # Maps normalized contract-type keywords to PDF category folder names.
        # Used to scope semantic retrieval to the matching category at audit time.
        self.contract_type_to_category: dict[str, str] = {
            "auto": "auto",
            "health": "health",
            "dental": "health",
            "vision": "health",
            "homeowners": "homeowners",
            "renters": "homeowners",
            "life": "life_other",
            "term life": "life_other",
            "whole life": "life_other",
        }
