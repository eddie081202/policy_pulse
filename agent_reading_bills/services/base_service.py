"""Base Service - Core service class with fundamental operations."""

import logging
from typing import Any, Dict
from ..entities.base_entity import BaseEntity


class BaseService:
    """
    Base service class providing common operations for all services.
    
    Provides:
    - Model dependency injection
    - Input validation
    - Error handling
    - Basic logging
    
    Attributes:
        model (BaseEntity): The entity providing configuration and state
    """
    
    def __init__(self, model: BaseEntity):
        """
        Initialize the service with a model entity.
        
        Args:
            model (BaseEntity): Entity providing configuration and state
        
        Raises:
            TypeError: If model is not a BaseEntity instance
        """
        if not isinstance(model, BaseEntity):
            raise TypeError(f"model must be a BaseEntity instance, got {type(model)}")
        
        self._model = model
        
        # Setup logging
        self._logger = logging.getLogger(self.__class__.__name__)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)
    
    @property
    def model(self) -> BaseEntity:
        """Get the model entity."""
        return self._model
    
    def _validate_input(self, value: Any, expected_type: type, field_name: str = "value") -> None:
        """
        Validate input against expected type.
        
        Args:
            value: The value to validate
            expected_type: Expected type (or tuple of types)
            field_name: Name of the field for error messages
        
        Raises:
            TypeError: If value is not of expected type
            ValueError: If value is None or empty (for strings)
        """
        if value is None:
            raise ValueError(f"{field_name} cannot be None")
        
        if not isinstance(value, expected_type):
            raise TypeError(
                f"{field_name} must be {expected_type}, got {type(value)}"
            )
        
        if isinstance(value, str) and not value.strip():
            raise ValueError(f"{field_name} cannot be empty")
    
    def _handle_error(self, error: Exception, operation: str = "operation") -> Dict[str, Any]:
        """
        Handle errors with logging and structured response.
        
        Args:
            error (Exception): The exception that occurred
            operation (str): Name of the operation that failed
        
        Returns:
            Dict: Structured error response with status, error type, and message
        """
        error_type = type(error).__name__
        error_message = str(error)
        
        self._logger.error(
            f"Error during {operation}: {error_type} - {error_message}",
            exc_info=True
        )
        
        return {
            "status": "error",
            "operation": operation,
            "error_type": error_type,
            "error_message": error_message
        }
    
    def _log_operation(self, operation: str, details: str = "", level: str = "info") -> None:
        """
        Log an operation for debugging and monitoring.
        
        Args:
            operation (str): Name of the operation
            details (str): Additional details about the operation
            level (str): Log level (info, debug, warning)
        """
        log_message = f"{operation}"
        if details:
            log_message += f" - {details}"
        
        if level.lower() == "debug":
            self._logger.debug(log_message)
        elif level.lower() == "warning":
            self._logger.warning(log_message)
        else:
            self._logger.info(log_message)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model})"
