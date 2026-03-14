import base64
import json
import os
import shutil
from pathlib import Path
from typing import Iterable, Literal, Optional

import pandas as pd
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
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
            "List of discrepancies found between the uploaded contract and the best-matching "
            "knowledge base contract. Each item must be a plain human-readable sentence string, "
            "e.g. 'Deductible is $2,000 in the upload but $1,000 in the knowledge base.' "
            "Return an empty list if no discrepancies are found."
        )
    )
    audit_verdict: Literal["PASS", "FAIL", "NEEDS_REVIEW"] = Field(
        description=(
            "PASS if the uploaded contract hit > 70% matches a knowledge base contract. "
            "FAIL if it cannot hit 70% confidence score from all knowledge base contracts. "
            "NEEDS_REVIEW if uncertain."
        )
    )
    explanation: str = Field(
        description="A concise narrative explanation of the audit decision."
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0."
    )


class AuditResult(BaseModel):
    file_name: str
    file_type: Literal["pdf", "image"]
    document_type: Literal["contract", "unknown"]
    extracted_fields: dict
    matched_context: str
    discrepancies: list[str]
    audit_verdict: Literal["PASS", "FAIL", "NEEDS_REVIEW"]
    explanation: str
    confidence: float


class AgentDocReaderService(BaseService):
    def __init__(self, entity: AgentDocReaderEntity):
        super().__init__(entity)
        self._merged_retriever = None
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
            documents.append(Document(page_content=text, metadata=metadata))
        return documents

    def _get_unified_chain(self):
        """Build and cache a single RAG chain that merges the CSV and PDF vectorstores."""
        if self._unified_chain is not None:
            return self._unified_chain

        os.environ["OPENAI_API_KEY"] = self.entity.api_key
        merged_retriever = self._get_merged_retriever()
        prompt = ChatPromptTemplate.from_template(self.entity.system_prompt)

        self._unified_chain = (
            {
                "context": merged_retriever | (lambda docs: "\n\n".join(d.page_content for d in docs)),
                "question": RunnablePassthrough(),
            }
            | prompt
            | ChatOpenAI(model=self.entity.llm_model_name, temperature=0)
            | StrOutputParser()
        )
        return self._unified_chain

    def _get_merged_retriever(self):
        """Build and cache the merged retriever (CSV + PDF) with no LLM step."""
        if self._merged_retriever is not None:
            return self._merged_retriever

        os.environ["OPENAI_API_KEY"] = self.entity.api_key
        embeddings = OpenAIEmbeddings(model=self.entity.embedding_model_name)

        csv_retriever = Chroma(
            collection_name=self.entity.collection_name,
            embedding_function=embeddings,
            persist_directory=self.entity.csv_vectorstore_path,
        ).as_retriever(search_kwargs={"k": self.entity.k})

        pdf_retriever = Chroma(
            collection_name=self.entity.pdf_collection_name,
            embedding_function=embeddings,
            persist_directory=self.entity.pdf_vectorstore_path,
        ).as_retriever(search_kwargs={"k": self.entity.k})

        def _merge(query: str) -> list[Document]:
            return csv_retriever.invoke(query) + pdf_retriever.invoke(query)

        self._merged_retriever = RunnableLambda(_merge)
        return self._merged_retriever

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

    def _exact_pdf_lookup(self, policy_number: str) -> list[str]:
        """Direct text search in pdf_chunks.jsonl for a specific policy number.

        Semantic search is unreliable for exact identifiers. This guarantees
        we find the document if it exists in the knowledge base.
        """
        jsonl_path = Path(self.entity.pdf_chunks_path)
        if not jsonl_path.exists():
            return []
        matches = []
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                row = line.strip()
                if not row:
                    continue
                record = json.loads(row)
                if policy_number in record.get("text", ""):
                    matches.append(record["text"])
        return matches

    def _cross_reference(self, extracted_fields: dict) -> str:
        """Retrieve matching contract records from the knowledge base.

        Priority 1 — exact policy number lookup directly in the JSONL (deterministic).
        Priority 2 — semantic retrieval from both vectorstores for broader context.
        """
        sections: list[str] = []

        # Priority 1: exact match by policy number
        policy_number = extracted_fields.get("policy_number")
        if policy_number:
            exact_chunks = self._exact_pdf_lookup(policy_number)
            if exact_chunks:
                header = f"=== EXACT MATCH (policy number: {policy_number}) ==="
                sections.append(header + "\n\n" + "\n\n---\n\n".join(exact_chunks))

        # Priority 2: semantic retrieval
        parts = []
        for key in ("contract_type", "coverage_category", "policy_number", "contract_id"):
            val = extracted_fields.get(key)
            if val:
                parts.append(f"{key.replace('_', ' ')} {val}")
        parts.append("deductible copay exclusions coverage terms")
        query = " ".join(parts)
        docs: list[Document] = self._get_merged_retriever().invoke(query)
        if docs:
            sections.append(
                "=== SEMANTIC RESULTS ===\n\n"
                + "\n\n---\n\n".join(doc.page_content for doc in docs)
            )

        return "\n\n" + ("=" * 60) + "\n\n".join(sections)

    def _run_audit(
        self,
        file_name: str,
        file_type: str,
        extracted_fields: dict,
        context: str,
    ) -> "AuditResult":
        """Ask the LLM to compare the uploaded contract against existing data."""
        os.environ["OPENAI_API_KEY"] = self.entity.api_key
        llm = ChatOpenAI(model=self.entity.llm_model_name, temperature=0)
        structured_llm = llm.with_structured_output(_AuditLLMOutput, method="function_calling")

        prompt = (
            "You are an expert insurance contract analyst.\n\n"
            "STEP 1 — Find the best match: From the knowledge base documents below, identify the single "
            "contract that most closely matches the uploaded contract (prioritise: policy number, "
            "contract type, deductible, and premium).\n\n"
            "STEP 2 — Compare: Compare the uploaded contract fields only against that best-matching "
            "contract. List only genuine discrepancies between the two.\n\n"
            "STEP 3 — Verdict (choose exactly one):\n"
            "  • PASS — the uploaded contract's key fields (policy number, contract type, deductible, "
            "premium) match the best-matching knowledge base contract closely. Output has > 70% confidence.\n"
            "  • FAIL — the uploaded contract cannot hit 70% confidence score from all knowledge base contracts.\n"
            "  • NEEDS_REVIEW — partial match, or insufficient data to decide confidently.\n\n"
            f"Uploaded Contract Fields:\n{json.dumps(extracted_fields, indent=2)}\n\n"
            f"Knowledge Base Contracts (retrieved):\n{context}"
        )
        llm_output: _AuditLLMOutput = structured_llm.invoke(prompt)
        return AuditResult(
            file_name=file_name,
            file_type=file_type,
            document_type="contract",
            extracted_fields=extracted_fields,
            matched_context=context,
            discrepancies=llm_output.discrepancies,
            audit_verdict=llm_output.audit_verdict,
            explanation=llm_output.explanation,
            confidence=llm_output.confidence,
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def initialize_csv_vectorstore(self) -> None:
        os.environ["OPENAI_API_KEY"] = self.entity.api_key

        embeddings = OpenAIEmbeddings(model=self.entity.embedding_model_name)
        vectorstore = Chroma(
            collection_name=self.entity.collection_name,
            embedding_function=embeddings,
            persist_directory=self.entity.csv_vectorstore_path,
        )

        existing = vectorstore.get()
        if existing["ids"]:
            return

        documents = self._transform_csv()
        vectorstore.add_documents(documents)

    def query_contracts(self, question: str) -> str:
        """Query the unified contracts vectorstore (CSV + PDF) and return a natural language answer."""
        self.initialize_csv_vectorstore()
        if not Path(self.entity.pdf_vectorstore_path).exists():
            self.transform_pdf_for_rag()
            self.initialize_pdf_vectorstore()
        return self._get_unified_chain().invoke(question)

    def audit_document(self, file_path: str) -> AuditResult:
        """Ingest a user-uploaded contract file (PDF or image) and audit it against existing contracts.

        Args:
            file_path: Absolute path to the uploaded PDF or image file.

        Returns:
            AuditResult with extracted fields, matched context, discrepancies, and verdict.
        """
        self.initialize_csv_vectorstore()
        if not Path(self.entity.pdf_vectorstore_path).exists():
            self.transform_pdf_for_rag()
            self.initialize_pdf_vectorstore()

        text, file_type = self._ingest_file(file_path)
        extracted = self._extract_fields(text)
        context = self._cross_reference(extracted)
        return self._run_audit(Path(file_path).name, file_type, extracted, context)

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
            all_pages.extend(pages)

        chunks = self._split_documents(all_pages)

        self._ensure_output_dir()
        total_chunks = self._save_jsonl(self._build_records(chunks))

        return len(pdf_files), len(all_pages), total_chunks

    def initialize_pdf_vectorstore(self) -> int:
        """Initialize Chroma vectorstore from PDF chunks.

        Returns:
            Count of vectors created
        """
        texts, metadatas, ids = self._read_jsonl_records()
        self._maybe_reset_persist_dir()

        os.environ["OPENAI_API_KEY"] = self.entity.api_key
        embeddings = OpenAIEmbeddings(model=self.entity.embedding_model_name)

        vectorstore = Chroma.from_texts(
            texts=texts,
            embedding=embeddings,
            metadatas=metadatas,
            ids=ids,
            collection_name=self.entity.pdf_collection_name,
            persist_directory=self.entity.pdf_vectorstore_path,
        )

        return len(texts)

    # ------------------------------------------------------------------
    # PDF Private helpers
    # ------------------------------------------------------------------

    def _find_pdf_files(self) -> list[Path]:
        """Discover all PDF files in the configured directory."""
        pdf_dir = Path(self.entity.pdf_dir)
        if not pdf_dir.exists():
            raise FileNotFoundError(f"PDF directory not found: {pdf_dir}")
        return sorted([p for p in pdf_dir.glob("*.pdf") if p.is_file()])

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

    def _maybe_reset_persist_dir(self) -> None:
        """Delete existing vectorstore directory if it exists."""
        persist_path = Path(self.entity.pdf_vectorstore_path)
        if persist_path.exists():
            shutil.rmtree(persist_path)
