"""
LLM Client for GerdsenAI CLI.

This module handles communication with local AI models via OpenAI-compatible APIs.
"""

import asyncio
import json
import logging
import random
import time
from collections.abc import AsyncGenerator
from typing import Any
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel

from ..config.settings import Settings
from ..utils.display import show_error
from ..utils.performance import measure_performance

logger = logging.getLogger(__name__)

# Per-operation timeout configurations (in seconds)
OPERATION_TIMEOUTS = {
    "health": 2.0,  # Reduced from 5.0 for faster connection testing
    "models": 5.0,  # Reduced from 10.0
    "chat": 30.0,
    "stream": 30.0,
    "default": 30.0,
}

# Retry configuration
# Use 2 retries (total 3 attempts) to balance responsiveness and robustness.
# This aligns with unit test expectations for retry behavior.
MAX_RETRIES = 2
BASE_DELAY = 0.5  # Reduced from 1.0 for faster retries
MAX_DELAY = 2.0  # Reduced from 8.0
RETRY_EXCEPTIONS = (
    httpx.RequestError,
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
)


class ModelInfo(BaseModel):
    """Information about an available model."""

    id: str
    object: str = "model"
    created: int | None = None
    owned_by: str | None = None
    size: int | None = None
    description: str | None = None


class ChatMessage(BaseModel):
    """A chat message."""

    role: str  # "system", "user", "assistant"
    content: str


class ChatCompletionRequest(BaseModel):
    """Chat completion request payload."""

    model: str
    messages: list[ChatMessage]
    temperature: float = 0.7
    max_tokens: int | None = None
    stream: bool = False
    stop: str | list[str] | None = None


class ChatCompletionResponse(BaseModel):
    """Chat completion response."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[dict[str, Any]]
    usage: dict[str, int] | None = None


class LLMClient:
    """Client for communicating with local LLM servers.

    The retry behavior can be configured via application settings. If
    `Settings.max_retries` is provided it will override the module level
    `MAX_RETRIES` constant for this client instance. This makes the retry
    policy user-configurable without changing test expectations (tests still
    rely on module constant if settings value matches default).
    """

    def __init__(self, settings: Settings):
        """
        Initialize the LLM client.

        Args:
            settings: Application settings containing server configuration
        """
        self.settings = settings
        self.base_url = settings.llm_server_url.rstrip("/")

        # Configure HTTP client with connection pooling and limits
        limits = httpx.Limits(
            max_keepalive_connections=10, max_connections=20, keepalive_expiry=30.0
        )

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(OPERATION_TIMEOUTS["default"]),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "GerdsenAI-CLI/0.1.0",
            },
            follow_redirects=True,
            limits=limits,
        )

        self._is_connected = False
        self._available_models: list[ModelInfo] = []
        # Effective retry configuration (instance-scoped)
        self._max_retries = getattr(settings, "max_retries", MAX_RETRIES) or MAX_RETRIES

        # Performance tracking
        self._request_count = 0
        self._retry_count = 0
        self._total_request_time = 0.0

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

    async def _execute_with_retry(
        self,
        operation_name: str,
        operation_func,
        *args,
        max_retries: int | None = None,
        **kwargs,
    ) -> Any:
        """
        Execute an operation with retry logic and exponential backoff.

        Args:
            operation_name: Name of the operation for logging
            operation_func: The async function to execute
            max_retries: Maximum number of retries
            *args, **kwargs: Arguments to pass to the operation function

        Returns:
            Result of the operation function

        Raises:
            The last exception if all retries fail
        """
        # Determine effective retries (explicit argument > instance > module constant)
        effective_retries = (
            max_retries
            if max_retries is not None
            else (self._max_retries if self._max_retries is not None else MAX_RETRIES)
        )

        last_exception = None

        for attempt in range(effective_retries + 1):
            try:
                start_time = time.time()
                result = await operation_func(*args, **kwargs)

                # Track performance
                self._request_count += 1
                self._total_request_time += time.time() - start_time

                if attempt > 0:
                    logger.info(f"{operation_name} succeeded on attempt {attempt + 1}")

                return result

            except RETRY_EXCEPTIONS as e:
                last_exception = e
                self._retry_count += 1

                if attempt < effective_retries:
                    # Calculate delay with exponential backoff and jitter
                    delay = min(BASE_DELAY * (2**attempt), MAX_DELAY)
                    jitter = random.uniform(0, delay * 0.1)  # 10% jitter
                    total_delay = delay + jitter

                    logger.warning(
                        f"{operation_name} failed on attempt {attempt + 1}/{effective_retries + 1}: {e}. "
                        f"Retrying in {total_delay:.2f}s..."
                    )

                    await asyncio.sleep(total_delay)
                else:
                    logger.error(
                        f"{operation_name} failed after {effective_retries + 1} attempts: {e}"
                    )
                    raise

            except Exception as e:
                # Don't retry on non-network errors
                logger.error(f"{operation_name} failed with non-retryable error: {e}")
                raise

        # This should never be reached, but just in case
        if last_exception:
            raise last_exception

    @measure_performance("health")
    async def connect(self) -> bool:
        """
        Test connection to the LLM server.

        Returns:
            True if connection successful, False otherwise
        """

        async def _connect_impl() -> bool:
            # Try Ollama-specific endpoints first, then fallback to general ones
            health_endpoints = [
                "/api/tags",  # Ollama specific - lists models
                "/api/version",  # Ollama specific - version info
                "/v1/models",  # OpenAI compatible
                "/health",  # Generic health check
                "/",  # Root endpoint
            ]

            # Use health-specific timeout
            timeout = httpx.Timeout(OPERATION_TIMEOUTS["health"])

            for i, endpoint in enumerate(health_endpoints):
                try:
                    url = self._get_endpoint(endpoint)
                    print(
                        f"[DEBUG] Testing endpoint {i+1}/{len(health_endpoints)}: {url}"
                    )
                    logger.info(f"Testing connection to {url}")

                    # Wrap in asyncio.wait_for for additional timeout protection
                    response = await asyncio.wait_for(
                        self.client.get(url, timeout=timeout),
                        timeout=OPERATION_TIMEOUTS["health"] + 1.0,  # Extra buffer
                    )

                    print(f"[DEBUG] Response status: {response.status_code}")
                    print(f"[DEBUG] Response headers: {dict(response.headers)}")

                    # Show response content for debugging (limit to first 200 chars)
                    try:
                        content = response.text[:200]
                        if len(response.text) > 200:
                            content += "..."
                        print(f"[DEBUG] Response content: {content}")
                    except Exception:
                        print("[DEBUG] Response content: <unable to decode>")

                    if response.status_code == 200:
                        logger.info(
                            f"Successfully connected to LLM server at {self.base_url} via {endpoint}"
                        )
                        print(f"[DEBUG] Connection successful via {endpoint}")
                        self._is_connected = True
                        return True
                    else:
                        print(f"[DEBUG] Non-200 status code: {response.status_code}")

                except asyncio.TimeoutError:
                    print(
                        f"[DEBUG] Timeout on endpoint {endpoint} (>{OPERATION_TIMEOUTS['health']}s)"
                    )
                    logger.debug(f"Endpoint {endpoint} timed out")
                    continue
                except httpx.ConnectError as e:
                    print(f"[DEBUG] Connection error on {endpoint}: {e}")
                    print(
                        "[DEBUG] This usually means the server is not running or not accessible"
                    )
                    logger.debug(f"Endpoint {endpoint} connection failed: {e}")
                    continue
                except httpx.HTTPStatusError as e:
                    print(
                        f"[DEBUG] HTTP error on {endpoint}: {e.response.status_code} - {e}"
                    )
                    logger.debug(f"Endpoint {endpoint} HTTP error: {e}")
                    continue
                except httpx.RequestError as e:
                    print(f"[DEBUG] Request error on {endpoint}: {e}")
                    logger.debug(f"Endpoint {endpoint} request failed: {e}")
                    continue
                except Exception as e:
                    print(f"[DEBUG] Unexpected error on endpoint {endpoint}: {e}")
                    logger.debug(f"Unexpected error on endpoint {endpoint}: {e}")
                    continue

            # If none of the health endpoints work, raise an exception to trigger retry
            print(f"[DEBUG] All endpoints failed for {self.base_url}")
            print("[DEBUG] Common Ollama troubleshooting:")
            print("[DEBUG] 1. Make sure Ollama is running: 'ollama serve'")
            print(f"[DEBUG] 2. Check if Ollama is listening on {self.base_url}")
            print(f"[DEBUG] 3. Try: 'curl {self.base_url}/api/tags' to test manually")
            print("[DEBUG] 4. Verify Ollama version is compatible (>= 0.1.0)")
            raise httpx.ConnectError(
                f"Unable to connect to LLM server at {self.base_url} (tried {len(health_endpoints)} endpoints)"
            )

        try:
            print(f"[DEBUG] Starting connection test to {self.base_url}")
            return await self._execute_with_retry("Connection test", _connect_impl)
        except Exception as e:
            print(f"[DEBUG] Connection test failed completely: {e}")
            logger.error(f"Connection test failed after retries: {e}")
            show_error(
                f"Unable to connect to LLM server at {self.base_url}. Is Ollama running?"
            )
            return False

    @measure_performance("model_loading")
    async def list_models(self) -> list[ModelInfo]:
        """
        Get list of available models from the server.

        Returns:
            List of available models
        """

        async def _list_models_impl() -> list[ModelInfo]:
            # Use models-specific timeout
            timeout = httpx.Timeout(OPERATION_TIMEOUTS["models"])

            # Try primary endpoint first
            url = self._get_endpoint("/v1/models")
            try:
                response = await self.client.get(url, timeout=timeout)
                response.raise_for_status()

                data = response.json()
                return self._parse_models_response(data)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # Try alternative endpoints
                    alternative_endpoints = ["/api/models", "/models", "/api/v1/models"]
                    for endpoint in alternative_endpoints:
                        try:
                            url = self._get_endpoint(endpoint)
                            response = await self.client.get(url, timeout=timeout)
                            response.raise_for_status()

                            data = response.json()
                            return self._parse_models_response(data)

                        except Exception:
                            continue

                    # If all endpoints fail, return empty list
                    logger.warning("Could not retrieve model list from any endpoint")
                    return []
                else:
                    raise

        try:
            models = await self._execute_with_retry("List models", _list_models_impl)
            self._available_models = models
            logger.info(f"Found {len(models)} available models")
            return models
        except Exception as e:
            logger.error(f"Failed to list models after retries: {e}")
            show_error(f"Failed to list models: {e}")
            return []

    def _parse_models_response(self, data: dict[str, Any]) -> list[ModelInfo]:
        """Parse models response data into ModelInfo objects."""
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

        return models

    @measure_performance("chat")
    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stop: str | list[str] | None = None,
    ) -> str | None:
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

        async def _chat_impl() -> str | None:
            # Use current model if not specified
            if not model:
                current_model = self.settings.current_model
                if not current_model:
                    # Try to get first available model
                    models = await self.list_models()
                    if models:
                        current_model = models[0].id
                    else:
                        show_error("No model specified and no models available")
                        return None
            else:
                current_model = model

            # Prepare request
            request_data = ChatCompletionRequest(
                model=current_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop,
                stream=False,
            )

            # Use chat-specific timeout
            timeout = httpx.Timeout(OPERATION_TIMEOUTS["chat"])

            # Try primary endpoint
            url = self._get_endpoint("/v1/chat/completions")
            try:
                response = await self.client.post(
                    url, json=request_data.model_dump(), timeout=timeout
                )
                response.raise_for_status()

                data = response.json()
                return self._parse_chat_response(data)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # Try alternative endpoint
                    url = self._get_endpoint("/api/chat")
                    response = await self.client.post(
                        url, json=request_data.model_dump(), timeout=timeout
                    )
                    response.raise_for_status()
                    data = response.json()

                    # Handle different response formats
                    if "response" in data:
                        return data["response"]
                    elif "message" in data:
                        return data["message"]

                    return self._parse_chat_response(data)
                else:
                    raise

        try:
            return await self._execute_with_retry("Chat completion", _chat_impl)
        except Exception as e:
            logger.error(f"Chat request failed after retries: {e}")
            show_error(f"Chat request failed: {e}")
            return None

    def _parse_chat_response(self, data: dict[str, Any]) -> str | None:
        """Parse chat completion response data."""
        # Extract response text
        if "choices" in data and len(data["choices"]) > 0:
            choice = data["choices"][0]
            if "message" in choice:
                return choice["message"].get("content", "")
            elif "text" in choice:
                return choice["text"]

        logger.warning("Invalid response format from LLM server")
        return None

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stop: str | list[str] | None = None,
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
                stream=True,
            )

            url = self._get_endpoint("/v1/chat/completions")

            async with self.client.stream(
                "POST", url, json=request_data.model_dump()
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
    def available_models(self) -> list[ModelInfo]:
        """Get cached list of available models."""
        return self._available_models.copy()

    @measure_performance("health")
    async def health_check(self) -> dict[str, Any]:
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
            "error": None,
            "retry_count": self._retry_count,
            "avg_response_time_ms": self._get_avg_response_time_ms(),
        }

        try:
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

    def _get_avg_response_time_ms(self) -> int | None:
        """Get average response time in milliseconds."""
        if self._request_count > 0:
            avg_time_s = self._total_request_time / self._request_count
            return int(avg_time_s * 1000)
        return None

    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics for the LLM client."""
        return {
            "total_requests": self._request_count,
            "total_retries": self._retry_count,
            "avg_response_time_ms": self._get_avg_response_time_ms(),
            "retry_rate_percent": (self._retry_count / max(self._request_count, 1))
            * 100,
            "total_request_time_s": self._total_request_time,
        }
