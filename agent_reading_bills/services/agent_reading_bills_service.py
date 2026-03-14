"""Agent Reading Bills Service - Main service for processing bill images and extracting information."""

import base64
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

import requests

from .base_service import BaseService
from ..entities.agent_reading_bills_entity import AgentReadingBillsEntity


class AgentReadingBillsService(BaseService):
    """
    Service for reading and analyzing bill images using OpenAI GPT-4 Vision.
    
    Integrates image processing, LLM calls, redaction, and JSON formatting
    to extract service information without exposing personal data.
    
    Methods:
        read_bill(image_path): Main entry point for processing a bill image
    """
    
    # Supported image formats
    SUPPORTED_IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    
    def __init__(self, model: AgentReadingBillsEntity):
        """
        Initialize the bill reading service.
        
        Args:
            model (AgentReadingBillsEntity): Configuration and prompts for the service
        
        Raises:
            TypeError: If model is not an AgentReadingBillsEntity instance
        """
        if not isinstance(model, AgentReadingBillsEntity):
            raise TypeError(
                f"model must be an AgentReadingBillsEntity instance, got {type(model)}"
            )
        super().__init__(model)
        self._model: AgentReadingBillsEntity = model
    
    def read_bill(self, image_path: str) -> Dict[str, Any]:
        """
        Read a bill image and extract service information.
        
        Main workflow:
        1. Validate and encode the image
        2. Call OpenAI GPT-4 Vision to analyze the bill
        3. Extract service information from the response
        4. Redact personal information
        5. Format output as JSON
        
        Args:
            image_path (str): Path to the bill image file
        
        Returns:
            Dict: Structured JSON with service information and redaction notes
        
        Example:
            >>> service = AgentReadingBillsService(entity)
            >>> result = service.read_bill("path/to/bill.jpg")
            >>> print(result['service_type'])  # "utility"
        """
        try:
            self._validate_input(image_path, str, "image_path")
            self._validate_image_exists(image_path)
            
            image_base64 = self._encode_image_to_base64(image_path)
            image_extension = self._get_image_extension(image_path)
            
            # Call OpenAI Vision API
            llm_response = self._call_openai(image_base64, image_extension)
            
            if "error" in llm_response:
                return llm_response
            
            # Extract service information
            service_info = self._extract_service_info(llm_response)
            
            # Format output as JSON
            formatted_output = self._format_output_json(service_info)
            
            return formatted_output
            
        except Exception as e:
            return self._handle_error(e, "read_bill")
    
    # ==================== Image Processing Methods ====================
    
    def _validate_image_exists(self, image_path: str) -> None:
        """
        Validate that the image file exists.
        
        Args:
            image_path (str): Path to the image file
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is not supported
        """
        path = Path(image_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        if not path.is_file():
            raise ValueError(f"Path is not a file: {image_path}")
        
        extension = path.suffix.lower()
        if extension not in self.SUPPORTED_IMAGE_FORMATS:
            raise ValueError(
                f"Unsupported image format: {extension}. "
                f"Supported formats: {', '.join(self.SUPPORTED_IMAGE_FORMATS)}"
            )
    
    def _encode_image_to_base64(self, image_path: str) -> str:
        """
        Encode an image file to base64 string.
        
        Args:
            image_path (str): Path to the image file
        
        Returns:
            str: Base64 encoded image data
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    
    def _get_image_extension(self, image_path: str) -> str:
        """
        Get the image file extension and map to media type.
        
        Args:
            image_path (str): Path to the image file
        
        Returns:
            str: Media type (e.g., "image/jpeg", "image/png")
        """
        extension = Path(image_path).suffix.lower()
        
        media_type_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }
        
        return media_type_map.get(extension, "image/jpeg")
    
    # ==================== LLM API Methods ====================
    
    def _call_openai(self, image_base64: str, media_type: str) -> Dict[str, Any]:
        """
        Call OpenAI GPT-4 Vision API to analyze the bill image.
        
        Args:
            image_base64 (str): Base64 encoded image
            media_type (str): Image media type (e.g., "image/jpeg")
        
        Returns:
            Dict: API response with bill analysis or error information
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._model.api_key}"
            }
            
            # Build the message with image
            payload = {
                "model": self._model.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": self._model.get_extraction_prompt()
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "response_format": {"type": "json_object"},
                "max_tokens": 4000
            }
            
            response = requests.post(
                self._model.OPENAI_API_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            # Check if response is successful
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    if "error" in error_json:
                        error_detail = error_json["error"].get("message", response.text)
                except:
                    pass
                
                return {
                    "error": f"API request failed with status {response.status_code}",
                    "error_type": "api_error",
                    "status_code": response.status_code,
                    "details": error_detail
                }
            
            result = response.json()
            
            # Extract the assistant's message
            if "choices" in result and len(result["choices"]) > 0:
                message_content = result["choices"][0]["message"]["content"]
                return {"response": message_content}
            else:
                return {
                    "error": "Unexpected API response format",
                    "raw_response": result
                }
            
        except requests.exceptions.RequestException as e:
            return {
                "error": f"API request failed: {str(e)}",
                "error_type": "api_error"
            }
        except Exception as e:
            return self._handle_error(e, "_call_openai")
    
    # ==================== Data Processing Methods ====================
    
    def _extract_service_info(self, llm_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse JSON service information from the LLM response.
        
        With response_format forced to JSON, the response is guaranteed to be valid JSON.
        
        Args:
            llm_response (Dict): Response from OpenAI Vision API
        
        Returns:
            Dict: Extracted service information or error
        """
        try:
            if "error" in llm_response:
                return llm_response
            
            response_text = llm_response.get("response", "")
            service_info = json.loads(response_text)
            
            return service_info
            
        except Exception as e:
            return self._handle_error(e, "_extract_service_info")
    
    def _redact_personal_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact personal information from extracted data.
        
        Uses the redaction fields from the entity to identify and mask sensitive info.
        
        Args:
            data (Dict): Extracted service information
        
        Returns:
            Dict: Data with personal information redacted
        """
        try:
            if "error" in data:
                return data
            
            # Create a deep copy to avoid modifying original
            redacted_data = json.loads(json.dumps(data))
            
            redaction_fields = set(f.lower() for f in self._model.redaction_fields)
            
            # Recursively redact sensitive fields
            self._redact_dict(redacted_data, redaction_fields)
            
            return redacted_data
            
        except Exception as e:
            return self._handle_error(e, "_redact_personal_info")
    
    def _redact_dict(self, obj: Any, redaction_fields: set, depth: int = 0) -> None:
        """
        Recursively redact sensitive fields in a dictionary or list.
        
        Args:
            obj: Object to redact (dict, list, or value)
            redaction_fields: Set of field names to redact (lowercase)
            depth: Current recursion depth (to prevent infinite recursion)
        """
        if depth > 20:  # Prevent infinite recursion
            return
        
        if isinstance(obj, dict):
            for key, value in list(obj.items()):
                if key.lower() in redaction_fields:
                    obj[key] = "[REDACTED]"
                elif isinstance(value, (dict, list)):
                    self._redact_dict(value, redaction_fields, depth + 1)
        
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, (dict, list)):
                    self._redact_dict(item, redaction_fields, depth + 1)
    
    def _format_output_json(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact personal information and add redaction notes to the extracted data.
        
        The LLM already returns the complete schema with all required fields.
        This function handles redaction and adds documentation of what was masked.
        
        Args:
            data (Dict): Extracted service information from LLM
        
        Returns:
            Dict: Data with personal information redacted and notes added
        """
        try:
            if "error" in data:
                return data
            
            # Redact personal information
            redacted_data = self._redact_personal_info(data)
            
            if "error" in redacted_data:
                return redacted_data
            
            # Add redaction notes
            redacted_data["redaction_notes"] = self._build_redaction_notes(redacted_data)
            
            return redacted_data
            
        except Exception as e:
            return self._handle_error(e, "_format_output_json")
    
    def _build_redaction_notes(self, data: Dict[str, Any]) -> list:
        """
        Build notes about what information was redacted.
        
        Args:
            data (Dict): Processed data
        
        Returns:
            list: List of redaction notes
        """
        notes = []
        
        # Check for redacted values in the data
        redacted_fields = set()
        self._find_redacted_fields(data, redacted_fields)
        
        if redacted_fields:
            notes.append(f"Redacted fields: {', '.join(sorted(redacted_fields))}")
        
        if not notes:
            notes.append("Personal information has been masked")
        
        return notes
    
    def _find_redacted_fields(self, obj: Any, redacted_set: set, depth: int = 0) -> None:
        """
        Recursively find redacted field names.
        
        Args:
            obj: Object to search
            redacted_set: Set to store found redacted field names
            depth: Current recursion depth
        """
        if depth > 20:
            return
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                if value == "[REDACTED]" or value == "[MASKED]":
                    redacted_set.add(key)
                elif isinstance(value, (dict, list)):
                    self._find_redacted_fields(value, redacted_set, depth + 1)
        
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    self._find_redacted_fields(item, redacted_set, depth + 1)
    
    def __repr__(self) -> str:
        return f"AgentReadingBillsService(model={self._model})"
