"""
LLM Client for GerdsenAI CLI.

This module handles communication with local AI models via OpenAI-compatible APIs.
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseModel

from ..config.settings import Settings
from ..utils.display import show_error, show_info, show_warning

logger = logging.getLogger(__name__)


class ModelInfo(BaseModel):
    """Information about an available model."""
    id: str
    object: str = "model"
    created: Optional[int] = None
    owned_by: Optional[str] = None
    size: Optional[int] = None
    description: Optional[str] = None


class ChatMessage(BaseModel):
    """A chat message."""
    role: str  # "system", "user", "assistant"
    content: str


class ChatCompletionRequest(BaseModel):
    """Chat completion request payload."""
    model: str
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    stop: Optional[Union[str, List[str]]] = None


class ChatCompletionResponse(BaseModel):
    """Chat completion response."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None


class LLMClient:
    """Client for communicating with local LLM servers."""
    
    def __init__(self, settings: Settings):
        """
        Initialize the LLM client.
        
        Args:
            settings: Application settings containing server configuration
        """
        self.settings = settings
        self.base_url = settings.llm_server_url.rstrip('/')
        
        # Configure HTTP client
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.api_timeout),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "GerdsenAI-CLI/0.1.0"
            },
            follow_redirects=True
        )
        
        self._is_connected = False
        self._available_models: List[ModelInfo] = []
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
    
    def _get_endpoint(self, path: str) -> str:
        """
        Get full endpoint URL.
        
        Args:
            path: API endpoint path
            
        Returns:
            Full URL for the endpoint
        """
        return urljoin(self.base_url + "/", path.lstrip("/"))
    
    async def connect(self) -> bool:
        """
        Test connection to the LLM server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to get server health/status
            health_endpoints = ["/health", "/v1/models", "/api/health", "/"]
            
            for endpoint in health_endpoints:
                try:
                    url = self._get_endpoint(endpoint)
                    response = await self.client.get(url)
                    
                    if response.status_code == 200:
                        logger.info(f"Successfully connected to LLM server at {self.base_url}")
                        self._is_connected = True
                        return True
                        
                except (httpx.RequestError, httpx.HTTPStatusError):
                    continue
            
            # If none of the health endpoints work, the server might be down
            show_error(f"Unable to connect to LLM server at {self.base_url}")
            return False
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            show_error(f"Connection test failed: {e}")
            return False
    
    async def list_models(self) -> List[ModelInfo]:
        """
        Get list of available models from the server.
        
        Returns:
            List of available models
        """
        try:
            url = self._get_endpoint("/v1/models")
            response = await self.client.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            # Handle different response formats
            if "data" in data:
                models_data = data["data"]
            elif "models" in data:
                models_data = data["models"]
            elif isinstance(data, list):
                models_data = data
            else:
                # Fallback for non-standard responses
                models_data = [{"id": "default", "object": "model"}]
            
            models = []
            for model_data in models_data:
                try:
                    if isinstance(model_data, str):
                        # Handle simple string lists
                        model = ModelInfo(id=model_data)
                    else:
                        # Handle object format
                        model = ModelInfo(**model_data)
                    models.append(model)
                except Exception as e:
                    logger.warning(f"Failed to parse model data: {model_data}, error: {e}")
                    continue
            
            self._available_models = models
            logger.info(f"Found {len(models)} available models")
            return models
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Try alternative endpoints
                alternative_endpoints = ["/api/models", "/models", "/api/v1/models"]
                for endpoint in alternative_endpoints:
                    try:
                        url = self._get_endpoint(endpoint)
                        response = await self.client.get(url)
                        response.raise_for_status()
                        
                        data = response.json()
                        # Process similar to above...
                        if "data" in data:
                            models_data = data["data"]
                        elif isinstance(data, list):
                            models_data = data
                        else:
                            continue
                        
                        models = []
                        for model_data in models_data:
                            if isinstance(model_data, str):
                                model = ModelInfo(id=model_data)
                            else:
                                model = ModelInfo(**model_data)
                            models.append(model)
                        
                        self._available_models = models
                        return models
                        
                    except Exception:
                        continue
                
                # If all endpoints fail, return empty list
                show_warning("Could not retrieve model list from server")
                return []
            else:
                raise
                
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            show_error(f"Failed to list models: {e}")
            return []
    
    async def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[Union[str, List[str]]] = None
    ) -> Optional[str]:
        """
        Send a chat completion request.
        
        Args:
            messages: List of chat messages
            model: Model to use (defaults to current model in settings)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stop: Stop sequences
            
        Returns:
            Generated response text, or None if failed
        """
        try:
            # Use current model if not specified
            if not model:
                model = self.settings.current_model
                if not model:
                    # Try to get first available model
                    models = await self.list_models()
                    if models:
                        model = models[0].id
                    else:
                        show_error("No model specified and no models available")
                        return None
            
            # Prepare request
            request_data = ChatCompletionRequest(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop,
                stream=False
            )
            
            url = self._get_endpoint("/v1/chat/completions")
            response = await self.client.post(
                url,
                json=request_data.model_dump()
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract response text
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                if "message" in choice:
                    return choice["message"].get("content", "")
                elif "text" in choice:
                    return choice["text"]
            
            show_error("Invalid response format from LLM server")
            return None
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Try alternative endpoint
                try:
                    url = self._get_endpoint("/api/chat")
                    response = await self.client.post(
                        url,
                        json=request_data.model_dump()
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    # Handle different response formats
                    if "response" in data:
                        return data["response"]
                    elif "message" in data:
                        return data["message"]
                    
                except Exception:
                    pass
            
            logger.error(f"Chat request failed: {e}")
            show_error(f"Chat request failed: HTTP {e.response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"Chat request failed: {e}")
            show_error(f"Chat request failed: {e}")
            return None
    
    async def stream_chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[Union[str, List[str]]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Send a streaming chat completion request.
        
        Args:
            messages: List of chat messages
            model: Model to use (defaults to current model in settings)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stop: Stop sequences
            
        Yields:
            Chunks of generated text
        """
        try:
            # Use current model if not specified
            if not model:
                model = self.settings.current_model
                if not model:
                    # Try to get first available model
                    models = await self.list_models()
                    if models:
                        model = models[0].id
                    else:
                        show_error("No model specified and no models available")
                        return
            
            # Prepare request
            request_data = ChatCompletionRequest(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop,
                stream=True
            )
            
            url = self._get_endpoint("/v1/chat/completions")
            
            async with self.client.stream(
                "POST",
                url,
                json=request_data.model_dump()
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        
                        if data_str.strip() == "[DONE]":
                            break
                        
                        try:
                            data = json.loads(data_str)
                            
                            if "choices" in data and len(data["choices"]) > 0:
                                choice = data["choices"][0]
                                if "delta" in choice and "content" in choice["delta"]:
                                    content = choice["delta"]["content"]
                                    if content:
                                        yield content
                                        
                        except json.JSONDecodeError:
                            # Skip invalid JSON lines
                            continue
                            
        except Exception as e:
            logger.error(f"Streaming chat request failed: {e}")
            show_error(f"Streaming chat request failed: {e}")
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected to server."""
        return self._is_connected
    
    @property
    def available_models(self) -> List[ModelInfo]:
        """Get cached list of available models."""
        return self._available_models.copy()
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the LLM server.
        
        Returns:
            Dictionary with health check results
        """
        health_info = {
            "server_url": self.base_url,
            "connected": False,
            "models_available": 0,
            "response_time_ms": None,
            "error": None
        }
        
        try:
            import time
            start_time = time.time()
            
            # Test connection
            connected = await self.connect()
            health_info["connected"] = connected
            
            if connected:
                # Get models
                models = await self.list_models()
                health_info["models_available"] = len(models)
                
                # Calculate response time
                end_time = time.time()
                health_info["response_time_ms"] = int((end_time - start_time) * 1000)
            
        except Exception as e:
            health_info["error"] = str(e)
        
        return health_info
