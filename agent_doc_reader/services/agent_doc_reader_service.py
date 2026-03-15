import base64
import json
import os
from pathlib import Path
from typing import Iterable, Literal, Optional

import pandas as pd
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel

from langchain_community.document_loaders import PyPDFLoader

from ..entities.agent_doc_reader_entity import AgentDocReaderEntity
from .base_service import BaseService

_SKIP_VALUES = {"n/a", "nan", "", "none"}

_IMAGE_MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "gif": "image/gif",
    "bmp": "image/bmp",
}

class _ContractFields(BaseModel):
    contract_id: Optional[str] = None
    policy_number: Optional[str] = None
    contract_type: Optional[str] = None
    coverage_category: Optional[str] = None
    inpatient_covered: Optional[str] = None
    outpatient_covered: Optional[str] = None
    dental_covered: Optional[str] = None
    exclusions: Optional[str] = None
    deductible_individual: Optional[str] = None
    copay_primary_care: Optional[str] = None
    premium_monthly: Optional[str] = None


from pydantic import BaseModel, Field


class _AuditLLMOutput(BaseModel):
    discrepancies: list[str] = Field(
        description=(
            "List of discrepancies found between the uploaded contract and any of the retrieved "
            "knowledge base contracts. Each item must be a plain human-readable sentence string, "
            "e.g. 'Deductible is $2,000 in the upload but $1,000 in the knowledge base.' "
            "Return an empty list if no discrepancies are found."
        )
    )
    audit_verdict: Literal["PASS", "FAIL", "NEEDS_REVIEW"] = Field(
        description=(
            "PASS if the uploaded contract's key fields are consistent with the knowledge base "
            "contracts at > 70% confidence. "
            "FAIL if it cannot reach 70% confidence against any knowledge base contract. "
            "NEEDS_REVIEW if uncertain."
        )
    )
    explanation: str = Field(
        description="A concise narrative explanation of the audit decision."
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0."
    )


class DocumentReference(BaseModel):
    """Structured pointer to a matched knowledge-base chunk.

    A downstream agent can use this to reload the original document
    without re-running the retrieval pipeline.
    """
    chunk_id: str = Field(description="Chunk or record identifier within the source file.")
    source_file: str = Field(description="Filename of the source document (PDF or CSV).")
    source_path: str = Field(description="Absolute path to the source file on disk.")
    category: Optional[str] = Field(
        default=None,
        description="Contract category folder ('auto', 'health', 'homeowners', 'life_other') or None for CSV.",
    )
    page: Optional[int] = Field(
        default=None,
        description="0-based page number within the source PDF; None for CSV records.",
    )
    text: str = Field(description="Raw chunk text as indexed in the vectorstore.")
    score: Optional[float] = Field(
        default=None,
        description="Retrieval relevance score (0.0–1.0). Reserved for future use; None until score-aware retrieval is enabled.",
    )


class AuditResult(BaseModel):
    file_name: str
    file_type: Literal["pdf", "image"]
    document_type: Literal["contract", "unknown"]
    extracted_fields: dict
    matched_documents: list[DocumentReference]
    discrepancies: list[str]
    audit_verdict: Literal["PASS", "FAIL", "NEEDS_REVIEW"]
    explanation: str
    confidence: float


class AgentDocReaderService(BaseService):
    def __init__(self, entity: AgentDocReaderEntity):
        super().__init__(entity)
        self._retriever = None
        self._unified_chain = None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _transform_csv(self) -> list[Document]:
        df = pd.read_csv(self.entity.csv_path)
        documents = []
        for _, row in df.iterrows():
            parts = []
            for col, val in row.items():
                str_val = str(val).strip()
                if str_val.lower() in _SKIP_VALUES:
                    continue
                label = col.replace("_", " ").title()
                parts.append(f"{label}: {str_val}")
            text = ". ".join(parts)
            metadata = {
                field: str(row[field]) for field in self.entity.metadata_fields
            }
            metadata["source_type"] = "csv"
            documents.append(Document(page_content=text, metadata=metadata))
        return documents

    def _get_unified_chain(self):
        """Build and cache a single RAG chain that merges the CSV and PDF vectorstores."""
        if self._unified_chain is not None:
            return self._unified_chain

        os.environ["OPENAI_API_KEY"] = self.entity.api_key
        retriever = self._get_retriever()
        prompt = ChatPromptTemplate.from_template(self.entity.system_prompt)

        self._unified_chain = (
            {
                "context": retriever | (lambda docs: "\n\n".join(d.page_content for d in docs)),
                "question": RunnablePassthrough(),
            }
            | prompt
            | ChatOpenAI(model=self.entity.llm_model_name, temperature=0)
            | StrOutputParser()
        )
        return self._unified_chain

    def _get_retriever(self, category: Optional[str] = None):
        """Build a retriever against the unified vectorstore.

        When *category* is provided, results are filtered to that category's PDF
        documents plus all CSV rows. The unfiltered retriever is cached.
        """
        os.environ["OPENAI_API_KEY"] = self.entity.api_key

        if category is None and self._retriever is not None:
            return self._retriever

        embeddings = OpenAIEmbeddings(model=self.entity.embedding_model_name)

        search_kwargs: dict = {"k": self.entity.k}
        if category is not None:
            search_kwargs["filter"] = {
                "$or": [{"source_type": "csv"}, {"category": category}]
            }

        retriever = Chroma(
            collection_name=self.entity.collection_name,
            embedding_function=embeddings,
            persist_directory=self.entity.vectorstore_path,
        ).as_retriever(search_kwargs=search_kwargs)

        if category is None:
            self._retriever = retriever

        return retriever

    # ------------------------------------------------------------------
    # Audit private helpers
    # ------------------------------------------------------------------

    def _ingest_file(self, file_path: str) -> tuple[str, str]:
        """Extract text from a PDF or image file.

        Returns:
            Tuple of (extracted_text, file_type) where file_type is 'pdf' or 'image'.
        """
        suffix = Path(file_path).suffix.lstrip(".").lower()

        if suffix == "pdf":
            pages = PyPDFLoader(file_path).load()
            text = "\n\n".join(p.page_content for p in pages)
            return text, "pdf"

        mime = _IMAGE_MIME.get(suffix)
        if mime is None:
            raise ValueError(f"Unsupported file type: .{suffix}")

        os.environ["OPENAI_API_KEY"] = self.entity.api_key
        b64 = base64.b64encode(Path(file_path).read_bytes()).decode()
        message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": (
                        "Transcribe all text visible in this insurance document image. "
                        "Preserve all field names, values, dates, and numbers exactly."
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                },
            ]
        )
        llm = ChatOpenAI(model=self.entity.llm_model_name, temperature=0)
        return llm.invoke([message]).content, "image"

    def _extract_fields(self, text: str) -> dict:
        """Extract structured contract fields from raw text."""
        os.environ["OPENAI_API_KEY"] = self.entity.api_key
        llm = ChatOpenAI(model=self.entity.llm_model_name, temperature=0)
        structured_llm = llm.with_structured_output(_ContractFields, method="function_calling")
        prompt = (
            "Extract the following fields from this insurance contract. "
            "If a field is not present, leave it as null.\n\n"
            f"{text}"
        )
        result: _ContractFields = structured_llm.invoke(prompt)
        return result.model_dump()

    def _detect_category(self, extracted_fields: dict) -> Optional[str]:
        """Derive the storage category from extracted contract fields.

        Checks 'contract_type' and 'coverage_category' against the entity's
        contract_type_to_category mapping using case-insensitive substring matching.
        Returns the matched category string, or None if the type is unknown.
        """
        mapping = self.entity.contract_type_to_category
        for field_key in ("contract_type", "coverage_category"):
            value = (extracted_fields.get(field_key) or "").lower()
            if not value:
                continue
            for keyword, category in mapping.items():
                if keyword in value:
                    return category
        return None

    def _build_document_reference(self, doc: Document) -> DocumentReference:
        """Build a structured DocumentReference from a retrieved LangChain Document.

        PDF chunks carry 'source_file', 'category', and optionally 'page' in their
        metadata (set during transform_pdf_for_rag). CSV Documents carry 'contract_id'
        and no 'source_file', so they are identified via entity.csv_path.
        """
        meta = doc.metadata or {}
        is_pdf = meta.get("source_type") == "pdf" or "source_file" in meta

        if is_pdf:
            source_file = meta["source_file"]
            category = meta.get("category")
            source_path = str(
                Path(self.entity.pdf_dir) / category / source_file
                if category
                else Path(self.entity.pdf_dir) / source_file
            )
            chunk_id = str(meta.get("chunk_id", ""))
            page = meta.get("page")  # int or None
        else:
            source_file = Path(self.entity.csv_path).name
            source_path = self.entity.csv_path
            category = None
            chunk_id = str(meta.get("contract_id", ""))
            page = None

        return DocumentReference(
            chunk_id=chunk_id,
            source_file=source_file,
            source_path=source_path,
            category=category,
            page=int(page) if page is not None else None,
            text=doc.page_content,
        )

    def _cross_reference(self, extracted_fields: dict) -> list[Document]:
        """Retrieve all matching contract records from the knowledge base via semantic search.

        When the contract type maps to a known category, retrieval is scoped to
        that category's documents. Otherwise the full knowledge base is searched.

        Returns:
            List of matched Document objects (empty list if none found).
        """
        parts = []
        for key in ("contract_type", "coverage_category", "policy_number", "contract_id"):
            val = extracted_fields.get(key)
            if val:
                parts.append(f"{key.replace('_', ' ')} {val}")
        parts.append("deductible copay exclusions coverage terms")
        query = " ".join(parts)

        category = self._detect_category(extracted_fields)
        return self._get_retriever(category).invoke(query)

    def _run_audit(
        self,
        file_name: str,
        file_type: str,
        extracted_fields: dict,
        docs: list[Document],
    ) -> "AuditResult":
        """Ask the LLM to compare the uploaded contract against all retrieved knowledge-base documents."""
        os.environ["OPENAI_API_KEY"] = self.entity.api_key
        llm = ChatOpenAI(model=self.entity.llm_model_name, temperature=0)
        structured_llm = llm.with_structured_output(_AuditLLMOutput, method="function_calling")

        context = (
            "=== RETRIEVED KNOWLEDGE BASE CONTRACTS ===\n\n"
            + "\n\n---\n\n".join(doc.page_content for doc in docs)
            if docs else ""
        )

        prompt = (
            "You are an expert insurance contract analyst.\n\n"
            "STEP 1 — Compare: Compare the uploaded contract fields against ALL knowledge base contracts "
            "listed below. Identify every genuine discrepancy between the uploaded contract and any of the "
            "retrieved contracts (differences in policy number, contract type, deductible, premium, "
            "coverage terms, exclusions, copays, etc.).\n\n"
            "STEP 2 — Verdict (choose exactly one):\n"
            "  • PASS — the uploaded contract's key fields (policy number, contract type, deductible, "
            "premium) are consistent with the knowledge base contracts at > 70% confidence.\n"
            "  • FAIL — the uploaded contract cannot reach 70% confidence against any knowledge base contract.\n"
            "  • NEEDS_REVIEW — partial matches, conflicting evidence, or insufficient data to decide confidently.\n\n"
            f"Uploaded Contract Fields:\n{json.dumps(extracted_fields, indent=2)}\n\n"
            f"Knowledge Base Contracts (retrieved):\n{context}"
        )
        llm_output: _AuditLLMOutput = structured_llm.invoke(prompt)

        references = [self._build_document_reference(doc) for doc in docs]

        return AuditResult(
            file_name=file_name,
            file_type=file_type,
            document_type="contract",
            extracted_fields=extracted_fields,
            matched_documents=references,
            discrepancies=llm_output.discrepancies,
            audit_verdict=llm_output.audit_verdict,
            explanation=llm_output.explanation,
            confidence=llm_output.confidence,
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def initialize_vectorstore(self) -> int:
        """Initialize the unified Chroma vectorstore with both CSV and PDF data.

        Skips ingestion if the collection is already populated.

        Returns:
            Total number of vectors in the collection.
        """
        os.environ["OPENAI_API_KEY"] = self.entity.api_key
        embeddings = OpenAIEmbeddings(model=self.entity.embedding_model_name)
        vectorstore = Chroma(
            collection_name=self.entity.collection_name,
            embedding_function=embeddings,
            persist_directory=self.entity.vectorstore_path,
        )

        existing = vectorstore.get()
        if existing["ids"]:
            return len(existing["ids"])

        # Ingest CSV rows
        vectorstore.add_documents(self._transform_csv())

        # Ingest PDF chunks (build JSONL first if not already done)
        if not Path(self.entity.pdf_chunks_path).exists():
            self.transform_pdf_for_rag()
        texts, metadatas, ids = self._read_jsonl_records()
        vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)

        return len(vectorstore.get()["ids"])

    def query_contracts(self, question: str) -> str:
        """Query the unified contracts vectorstore (CSV + PDF) and return a natural language answer."""
        self.initialize_vectorstore()
        return self._get_unified_chain().invoke(question)

    def audit_document(self, file_path: str) -> AuditResult:
        """Ingest a user-uploaded contract file (PDF or image) and audit it against existing contracts.

        Args:
            file_path: Absolute path to the uploaded PDF or image file.

        Returns:
            AuditResult with extracted fields, matched context, discrepancies, and verdict.
        """
        self.initialize_vectorstore()

        text, file_type = self._ingest_file(file_path)
        extracted = self._extract_fields(text)
        docs = self._cross_reference(extracted)
        return self._run_audit(Path(file_path).name, file_type, extracted, docs)

    # ------------------------------------------------------------------
    # PDF Transformation: Load → Chunk → Serialize to JSONL
    # ------------------------------------------------------------------

    def transform_pdf_for_rag(self) -> tuple[int, int, int]:
        """Transform PDF documents into chunked JSONL records.

        Returns:
            Tuple of (pdf_count, page_count, chunk_count)
        """
        pdf_files = self._find_pdf_files()
        if not pdf_files:
            raise FileNotFoundError(f"No PDF files found in: {self.entity.pdf_dir}")

        all_pages = []
        for pdf_file in pdf_files:
            pages = self._load_pages_from_pdf(pdf_file)
            for page in pages:
                page.metadata["source_file"] = pdf_file.name
                page.metadata["category"] = pdf_file.parent.name
                page.metadata["source_type"] = "pdf"
            all_pages.extend(pages)

        chunks = self._split_documents(all_pages)

        self._ensure_output_dir()
        total_chunks = self._save_jsonl(self._build_records(chunks))

        return len(pdf_files), len(all_pages), total_chunks

    # ------------------------------------------------------------------
    # PDF Private helpers
    # ------------------------------------------------------------------

    def _find_pdf_files(self) -> list[Path]:
        """Discover all PDF files recursively under the configured directory."""
        pdf_dir = Path(self.entity.pdf_dir)
        if not pdf_dir.exists():
            raise FileNotFoundError(f"PDF directory not found: {pdf_dir}")
        return sorted([p for p in pdf_dir.rglob("*.pdf") if p.is_file()])

    def _load_pages_from_pdf(self, pdf_path: Path) -> list[Document]:
        """Load pages from a single PDF file."""
        loader = PyPDFLoader(str(pdf_path))
        return loader.load()

    def _split_documents(self, docs: list[Document]) -> list[Document]:
        """Split documents into chunks with overlap."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.entity.chunk_size,
            chunk_overlap=self.entity.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        return splitter.split_documents(docs)

    def _ensure_output_dir(self) -> None:
        """Create output directory for JSONL if it doesn't exist."""
        output_path = Path(self.entity.pdf_chunks_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    def _build_records(self, chunks: list[Document]) -> Iterable[dict]:
        """Build JSONL records from document chunks."""
        for idx, chunk in enumerate(chunks):
            metadata = dict(chunk.metadata)
            yield {
                "chunk_id": idx,
                "text": chunk.page_content,
                "metadata": metadata,
            }

    def _save_jsonl(self, records: Iterable[dict]) -> int:
        """Save records to JSONL file and return count."""
        output_path = Path(self.entity.pdf_chunks_path)
        count = 0
        with output_path.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=True) + "\n")
                count += 1
        return count

    def _read_jsonl_records(self) -> tuple[list[str], list[dict], list[str]]:
        """Read records from JSONL file."""
        jsonl_path = Path(self.entity.pdf_chunks_path)
        if not jsonl_path.exists():
            raise FileNotFoundError(f"Input JSONL not found: {jsonl_path}")

        texts: list[str] = []
        metadatas: list[dict] = []
        ids: list[str] = []

        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                row = line.strip()
                if not row:
                    continue

                payload = json.loads(row)
                text = payload.get("text", "")
                if not text:
                    continue

                chunk_id = str(payload.get("chunk_id", len(ids)))
                metadata = payload.get("metadata", {}) or {}
                texts.append(text)
                metadatas.append(metadata)
                ids.append(chunk_id)

        return texts, metadatas, ids


