import os
from pathlib import Path

from dotenv import load_dotenv


class BaseEntity:
    def __init__(
        self,
        llm_model_name: str,
        embedding_model_name: str,
        api_key: str = None,
    ):
        if api_key is None:
            load_dotenv(Path(__file__).parent.parent.parent / ".env")
            api_key = os.getenv("GEMINI_API_KEY")

        self.llm_model_name = llm_model_name
        self.embedding_model_name = embedding_model_name
        self.api_key = api_key
