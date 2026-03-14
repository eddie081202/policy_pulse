import os

import pandas as pd
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from ..entities.agent_doc_reader_entity import AgentDocReaderEntity
from .base_service import BaseService

_SKIP_VALUES = {"n/a", "nan", "", "none"}


class AgentDocReaderService(BaseService):
    def __init__(self, entity: AgentDocReaderEntity):
        super().__init__(entity)
        self._chain = None

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
