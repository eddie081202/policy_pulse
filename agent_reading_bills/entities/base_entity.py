"""Base Entity - Core entity class with fundamental model attributes."""

import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in root directory
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


class BaseEntity:
    """
    Base entity class representing the core state of the LLM model.
    
    Attributes:
        api_key (str): OpenAI API key loaded from environment
        model_name (str): Name/identifier of the LLM model being used
        initialized_at (datetime): Timestamp when entity was created
    """
    
    def __init__(self, api_key: str = None, model_name: str = "gpt-4-vision"):
        """
        Initialize the base entity with API key and model name.
        
        Args:
            api_key (str, optional): OpenAI API key. If None, loads from OPENAI_API_KEY env var
            model_name (str): LLM model identifier (default: gpt-4-vision)
        
        Raises:
            ValueError: If api_key is not provided and OPENAI_API_KEY env var is not set
        """
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "API key not provided. Please set OPENAI_API_KEY environment variable or pass api_key parameter."
                )
        
        self._api_key = api_key
        self._model_name = model_name
        self._initialized_at = datetime.now()
    
    @property
    def api_key(self) -> str:
        """Get the API key."""
        return self._api_key
    
    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self._model_name
    
    @property
    def initialized_at(self) -> datetime:
        """Get the initialization timestamp."""
        return self._initialized_at
    
    def __repr__(self) -> str:
        return (
            f"BaseEntity(model_name='{self.model_name}', "
            f"initialized_at={self.initialized_at.isoformat()})"
        )
