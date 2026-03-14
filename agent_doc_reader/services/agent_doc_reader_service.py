import json
import os
import shutil
from pathlib import Path
from typing import Iterable

import pandas as pd
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from langchain_community.document_loaders import PyPDFLoader
except ImportError:
    from langchain.document_loaders import PyPDFLoader

from ..entities.agent_doc_reader_entity import AgentDocReaderEntity
from .base_service import BaseService

_SKIP_VALUES = {"n/a", "nan", "", "none"}


class AgentDocReaderService(BaseService):
    def __init__(self, entity: AgentDocReaderEntity):
        super().__init__(entity)
        self._chain = None
        self._pdf_chain = None

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

    def _get_chain(self):
        if self._chain is not None:
            return self._chain

        os.environ["OPENAI_API_KEY"] = self.entity.api_key

        embeddings = OpenAIEmbeddings(model=self.entity.embedding_model_name)
        vectorstore = Chroma(
            collection_name=self.entity.collection_name,
            embedding_function=embeddings,
            persist_directory=self.entity.csv_vectorstore_path,
        )
        retriever = vectorstore.as_retriever(search_kwargs={"k": self.entity.k})

        prompt = ChatPromptTemplate.from_template(self.entity.system_prompt)

        self._chain = (
            {
                "context": retriever | (lambda docs: "\n\n".join(d.page_content for d in docs)),
                "question": RunnablePassthrough(),
            }
            | prompt
            | ChatOpenAI(model=self.entity.llm_model_name, temperature=0)
            | StrOutputParser()
        )
        return self._chain

    def _get_pdf_chain(self):
        """Build and cache the RAG chain for PDF queries."""
        if self._pdf_chain is not None:
            return self._pdf_chain

        os.environ["OPENAI_API_KEY"] = self.entity.api_key

        embeddings = OpenAIEmbeddings(model=self.entity.embedding_model_name)
        vectorstore = Chroma(
            collection_name=self.entity.pdf_collection_name,
            embedding_function=embeddings,
            persist_directory=self.entity.pdf_vectorstore_path,
        )
        retriever = vectorstore.as_retriever(search_kwargs={"k": self.entity.k})

        prompt = ChatPromptTemplate.from_template(self.entity.system_prompt)

        self._pdf_chain = (
            {
                "context": retriever | (lambda docs: "\n\n".join(d.page_content for d in docs)),
                "question": RunnablePassthrough(),
            }
            | prompt
            | ChatOpenAI(model=self.entity.llm_model_name, temperature=0)
            | StrOutputParser()
        )
        return self._pdf_chain

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

    def query(self, question: str) -> str:
        self.initialize_csv_vectorstore()
        return self._get_chain().invoke(question)

    def query_pdf(self, question: str) -> str:
        """Query the PDF vectorstore and return a natural language answer."""
        # Ensure vectorstore is initialized before querying
        if not Path(self.entity.pdf_vectorstore_path).exists():
            self.transform_pdf_for_rag()
            self.initialize_pdf_vectorstore()
        
        return self._get_pdf_chain().invoke(question)

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
