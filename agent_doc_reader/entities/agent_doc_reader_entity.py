from pathlib import Path

from .base_entity import BaseEntity

_ROOT = Path(__file__).parent.parent.parent


class AgentDocReaderEntity(BaseEntity):
    def __init__(
        self,
        llm_model_name: str = "gpt-4o",
        embedding_model_name: str = "text-embedding-3-small",
        api_key: str = None,
        # CSV configuration
        csv_path: str = None,
        csv_vectorstore_path: str = None,
        csv_collection_name: str = "insurance_contracts",
        csv_metadata_fields: set = None,
        # PDF configuration
        pdf_dir: str = None,
        pdf_chunks_path: str = None,
        pdf_vectorstore_path: str = None,
        pdf_collection_name: str = "insurance_contracts_pdf",
        chunk_size: int = 1200,
        chunk_overlap: int = 200,
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
        # CSV paths and configuration
        self.csv_path = csv_path or str(
            _ROOT / "data" / "insurance_contracts" / "insurance_contracts_10.csv"
        )
        self.csv_vectorstore_path = csv_vectorstore_path or str(
            _ROOT / "data" / "vectorstore" / "csv"
        )
        self.collection_name = csv_collection_name
        self.metadata_fields = csv_metadata_fields or {"contract_id", "contract_type", "policy_number"}
        
        # PDF paths and configuration
        self.pdf_dir = pdf_dir or str(
            _ROOT / "data" / "insurance_contracts"
        )
        self.pdf_chunks_path = pdf_chunks_path or str(
            _ROOT / "data" / "vectorstore" / "pdf_chunks.jsonl"
        )
        self.pdf_vectorstore_path = pdf_vectorstore_path or str(
            _ROOT / "data" / "vectorstore" / "pdf"
        )
        self.pdf_collection_name = pdf_collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Shared configuration
        self.k = k
        self.system_prompt = system_prompt
