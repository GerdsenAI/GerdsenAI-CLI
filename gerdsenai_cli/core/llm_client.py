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
# Significantly increased for local AI models which can be slow
OPERATION_TIMEOUTS = {
    "health": 10.0,  # Increased for slow local models
    "models": 30.0,  # Increased - model loading can be slow
    "chat": 600.0,  # 10 minutes for local AI inference
    "stream": 600.0,  # 10 minutes for streaming responses
    "default": 600.0,  # Default 10 minutes for safety
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

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the LLM client.

        Args:
            settings: Application settings containing server configuration
        """
        self.settings = settings
        self.base_url = settings.llm_server_url.rstrip("/")

        # Store client configuration (will be used to create client in async context)
        self._limits = httpx.Limits(
            max_keepalive_connections=10, max_connections=20, keepalive_expiry=30.0
        )

        # Use api_timeout from settings, fallback to default if not set
        self._default_timeout = getattr(
            settings, "api_timeout", OPERATION_TIMEOUTS["default"]
        )

        # Client will be created in __aenter__ (async context)
        self.client: httpx.AsyncClient | None = None

        self._is_connected = False
        self._available_models: list[ModelInfo] = []
        # Effective retry configuration (instance-scoped)
        # Use explicit None check to allow max_retries=0
        max_retries_from_settings = getattr(settings, "max_retries", None)
        self._max_retries = (
            MAX_RETRIES if max_retries_from_settings is None else max_retries_from_settings
        )

        # Performance tracking
        self._request_count = 0
        self._retry_count = 0
        self._total_request_time = 0.0

    async def __aenter__(self) -> "LLMClient":
        """Async context manager entry - create httpx.AsyncClient in async context."""
        # Create httpx.AsyncClient in the async event loop context
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._default_timeout),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "GerdsenAI-CLI/0.1.0",
            },
            follow_redirects=True,
            limits=self._limits,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client."""
        if self.client is not None:
            await self.client.aclose()

    def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized."""
        if self.client is None:
            raise RuntimeError(
                "LLMClient must be used within an async context manager (async with LLMClient(...))"
            )
        return self.client

    def _get_endpoint(self, path: str) -> str:
        """
        Get full endpoint URL.

        Args:
            path: API endpoint path

        Returns:
            Full URL for the endpoint
        """
        return urljoin(self.base_url + "/", path.lstrip("/"))

    def _get_timeout(self, operation: str) -> float:
        """
        Get timeout for a specific operation.

        Uses granular timeout settings from Settings if available, otherwise falls back to defaults.
        Priority: operation-specific setting > api_timeout > module constant

        Args:
            operation: Operation name (health, models, chat, stream, default)

        Returns:
            Timeout in seconds
        """
        # Map operation names to setting attribute names
        timeout_map: dict[str, str] = {
            "health": "health_check_timeout",
            "models": "model_list_timeout",
            "chat": "chat_timeout",
            "stream": "stream_timeout",
        }

        # Try to get operation-specific timeout from settings
        if operation in timeout_map:
            setting_attr = timeout_map[operation]
            if hasattr(self.settings, setting_attr):
                timeout_val = getattr(self.settings, setting_attr, None)
                if timeout_val and timeout_val > 0:
                    result: float = timeout_val
                    return result

        # Fallback to generic api_timeout
        if hasattr(self.settings, "api_timeout") and self.settings.api_timeout:
            return self.settings.api_timeout

        # Final fallback to operation-specific constant
        return OPERATION_TIMEOUTS.get(operation, OPERATION_TIMEOUTS["default"])

    async def _execute_with_retry(
        self,
        operation_name: str,
        operation_func: Any,
        *args: Any,
        max_retries: int | None = None,
        **kwargs: Any,
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

    @measure_performance("health")  # type: ignore[misc]
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
                    logger.debug(
                        f"Testing endpoint {i + 1}/{len(health_endpoints)}: {url}"
                    )
                    logger.info(f"Testing connection to {url}")

                    # Wrap in asyncio.wait_for for additional timeout protection
                    response = await asyncio.wait_for(
                        self._ensure_client().get(url, timeout=timeout),
                        timeout=OPERATION_TIMEOUTS["health"] + 1.0,  # Extra buffer
                    )

                    logger.debug(f"Response status: {response.status_code}")
                    logger.debug(f"Response headers: {dict(response.headers)}")

                    # Show response content for debugging (limit to first 200 chars)
                    try:
                        content = response.text[:200]
                        if len(response.text) > 200:
                            content += "..."
                        logger.debug(f"Response content: {content}")
                    except Exception as e:
                        logger.debug(f"Response content: <unable to decode - {e}>")

                    if response.status_code == 200:
                        logger.info(
                            f"Successfully connected to LLM server at {self.base_url} via {endpoint}"
                        )
                        logger.debug(f"Connection successful via {endpoint}")
                        self._is_connected = True
                        return True
                    else:
                        logger.debug(f"Non-200 status code: {response.status_code}")

                except TimeoutError:
                    logger.debug(
                        f"Timeout on endpoint {endpoint} (>{OPERATION_TIMEOUTS['health']}s)"
                    )
                    continue
                except httpx.ConnectError as e:
                    logger.debug(f"Connection error on {endpoint}: {e}")
                    logger.debug(
                        "This usually means the server is not running or not accessible"
                    )
                    continue
                except httpx.HTTPStatusError as e:
                    logger.debug(
                        f"HTTP error on {endpoint}: {e.response.status_code} - {e}"
                    )
                    continue
                except httpx.RequestError as e:
                    logger.debug(f"Request error on {endpoint}: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"Unexpected error on endpoint {endpoint}: {e}")
                    continue

            # If none of the health endpoints work, raise an exception to trigger retry
            logger.debug(f"All endpoints failed for {self.base_url}")
            logger.debug("Common troubleshooting steps:")
            logger.debug("1. Make sure your LLM server is running")
            logger.debug(f"2. Verify the server is listening on {self.base_url}")
            logger.debug(f"3. Test manually: 'curl {self.base_url}/v1/models'")
            logger.debug("4. Check server logs for errors")
            raise httpx.ConnectError(
                f"Unable to connect to LLM server at {self.base_url} (tried {len(health_endpoints)} endpoints)"
            )

        try:
            logger.debug(f"Starting connection test to {self.base_url}")
            result: bool = await self._execute_with_retry("Connection test", _connect_impl)
            return result
        except Exception as e:
            logger.debug(f"Connection test failed completely: {e}")
            logger.error(f"Connection test failed after retries: {e}")
            show_error(
                f"Unable to connect to LLM server at {self.base_url}. Is the server running?"
            )
            return False

    @measure_performance("model_loading")  # type: ignore[misc]
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
                response = await self._ensure_client().get(url, timeout=timeout)
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
                            response = await self._ensure_client().get(
                                url, timeout=timeout
                            )
                            response.raise_for_status()

                            data = response.json()
                            return self._parse_models_response(data)

                        except Exception as endpoint_error:
                            logger.debug(
                                f"Endpoint {endpoint} failed: {endpoint_error}"
                            )
                            continue

                    # If all endpoints fail, return empty list
                    logger.warning(
                        f"Could not retrieve model list from any endpoint (tried {len(alternative_endpoints)} alternatives)"
                    )
                    return []
                else:
                    raise

        try:
            models: list[ModelInfo] = await self._execute_with_retry("List models", _list_models_impl)
            self._available_models = models
            logger.info(f"Found {len(models)} available models")
            return models
        except Exception as e:
            logger.error(f"Failed to list models after retries: {e}")
            show_error(f"Failed to list models: {e}")
            return []

    def _parse_models_response(self, data: dict[str, Any] | list[Any]) -> list[ModelInfo]:
        """Parse models response data into ModelInfo objects."""
        # Handle different response formats
        if isinstance(data, dict):
            if "data" in data:
                models_data = data["data"]
            elif "models" in data:
                models_data = data["models"]
            else:
                # Fallback for non-standard responses
                models_data = [{"id": "default", "object": "model"}]
        else:  # isinstance(data, list)
            models_data = data

        models = []
        for model_data in models_data:
            try:
                if isinstance(model_data, str):
                    # Handle simple string lists
                    model = ModelInfo(id=model_data)
                else:
                    # Handle object format - convert str fields to int if needed
                    data = dict(model_data)
                    if "created" in data and isinstance(data["created"], str):
                        try:
                            data["created"] = int(data["created"])
                        except (ValueError, TypeError):
                            data.pop("created")
                    if "size" in data and isinstance(data["size"], str):
                        try:
                            data["size"] = int(data["size"])
                        except (ValueError, TypeError):
                            data.pop("size")
                    model = ModelInfo(**data)
                models.append(model)
            except Exception as e:
                logger.warning(f"Failed to parse model data: {model_data}, error: {e}")
                continue

        return models

    @measure_performance("chat")  # type: ignore[misc]
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

            # Use chat-specific timeout from settings or fallback
            timeout = httpx.Timeout(self._get_timeout("chat"))

            # Try primary endpoint
            url = self._get_endpoint("/v1/chat/completions")
            try:
                response = await self._ensure_client().post(
                    url, json=request_data.model_dump(), timeout=timeout
                )
                response.raise_for_status()

                data = response.json()
                return self._parse_chat_response(data)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # Try alternative endpoint
                    url = self._get_endpoint("/api/chat")
                    response = await self._ensure_client().post(
                        url, json=request_data.model_dump(), timeout=timeout
                    )
                    response.raise_for_status()
                    data = response.json()

                    # Handle different response formats
                    if "response" in data:
                        response_text: str = data["response"]
                        return response_text
                    elif "message" in data:
                        message_text: str = data["message"]
                        return message_text

                    return self._parse_chat_response(data)
                else:
                    raise

        try:
            result: str | None = await self._execute_with_retry("Chat completion", _chat_impl)
            return result
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
                content: str = choice["message"].get("content", "")
                return content
            elif "text" in choice:
                text: str = choice["text"]
                return text

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
            current_model = model
            if not current_model:
                current_model = self.settings.current_model
                if not current_model:
                    # Try to get first available model
                    models = await self.list_models()
                    if models:
                        current_model = models[0].id
                    else:
                        show_error("No model specified and no models available")
                        return

            # Prepare request
            request_data = ChatCompletionRequest(
                model=current_model if current_model is not None else "",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop,
                stream=True,
            )

            url = self._get_endpoint("/v1/chat/completions")

            async with self._ensure_client().stream(
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

    @measure_performance("health")  # type: ignore[misc]
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

    def get_model_context_window(self, model_id: str) -> int:
        """
        Auto-detect context window size for a given model.

        Uses pattern matching against known model families to determine
        the maximum context window size in tokens.

        Args:
            model_id: Model identifier (e.g., "gpt-4-turbo", "gemini-pro")

        Returns:
            Context window size in tokens (defaults to 4096 for unknown models)
        """
        model_lower = model_id.lower()

        # GPT-4 models (OpenAI)
        if "gpt-4-turbo" in model_lower or "gpt-4-1106" in model_lower:
            return 128_000  # 128K tokens
        elif "gpt-4-32k" in model_lower:
            return 32_768  # 32K tokens
        elif "gpt-4" in model_lower:
            return 8_192  # 8K tokens (base GPT-4)

        # GPT-3.5 models (OpenAI)
        elif "gpt-3.5-turbo-16k" in model_lower:
            return 16_384  # 16K tokens
        elif "gpt-3.5" in model_lower:
            return 4_096  # 4K tokens

        # Gemini models (Google)
        elif "gemini-pro" in model_lower or "gemini-1.5-pro" in model_lower:
            return 1_000_000  # 1M tokens
        elif "gemini" in model_lower:
            return 32_768  # 32K tokens (earlier Gemini models)

        # Claude models (Anthropic)
        elif "claude-3" in model_lower:
            return 200_000  # 200K tokens
        elif "claude-2" in model_lower:
            return 100_000  # 100K tokens
        elif "claude" in model_lower:
            return 100_000  # 100K tokens (default)

        # Llama models
        elif "llama-3" in model_lower or "llama3" in model_lower:
            if "70b" in model_lower or "405b" in model_lower:
                return 8_192  # 8K tokens for larger Llama 3
            return 8_192  # 8K tokens (Llama 3)
        elif "llama-2" in model_lower or "llama2" in model_lower:
            return 4_096  # 4K tokens (Llama 2)
        elif "llama" in model_lower:
            return 4_096  # 4K tokens (conservative default)

        # Mistral models
        elif "mixtral" in model_lower:
            return 32_768  # 32K tokens (Mixtral 8x7B)
        elif "mistral" in model_lower:
            if "7b" in model_lower:
                return 8_192  # 8K tokens (Mistral 7B)
            return 32_768  # 32K tokens (larger Mistral models)

        # Qwen models
        elif "qwen" in model_lower:
            if "72b" in model_lower or "110b" in model_lower:
                return 32_768  # 32K tokens for larger Qwen
            return 8_192  # 8K tokens (smaller Qwen models)

        # Yi models
        elif "yi-34b" in model_lower:
            return 200_000  # 200K tokens
        elif "yi" in model_lower:
            return 4_096  # 4K tokens (smaller Yi models)

        # DeepSeek models
        elif "deepseek" in model_lower:
            return 32_768  # 32K tokens

        # Phi models (Microsoft)
        elif "phi-3" in model_lower:
            return 128_000  # 128K tokens
        elif "phi" in model_lower:
            return 2_048  # 2K tokens (earlier Phi models)

        # Solar models
        elif "solar" in model_lower:
            return 4_096  # 4K tokens

        # Conservative default for unknown models
        else:
            logger.warning(
                f"Unknown model '{model_id}', defaulting to 4096 token context window. "
                "You can override this in settings."
            )
            return 4_096  # Conservative 4K default
