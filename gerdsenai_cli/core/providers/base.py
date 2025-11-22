"""
Base classes for LLM provider abstraction.

Defines the interface that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator


class ProviderType(Enum):
    """Types of LLM providers."""

    OLLAMA = "ollama"
    VLLM = "vllm"
    LM_STUDIO = "lm_studio"
    HUGGINGFACE_TGI = "huggingface_tgi"
    LOCALAI = "localai"
    LLAMA_CPP = "llama_cpp"
    TEXT_GEN_WEBUI = "text_gen_webui"
    KOBOLDAI = "koboldai"
    OPENAI_COMPATIBLE = "openai_compatible"  # Generic OpenAI-compatible


@dataclass
class ModelInfo:
    """Information about an available model."""

    name: str
    provider: ProviderType
    size: int | None = None  # Size in bytes
    quantization: str | None = None  # e.g., "Q4_K_M", "fp16"
    context_length: int | None = None  # Max context window
    parameters: dict[str, Any] = field(default_factory=dict)
    is_loaded: bool = False


@dataclass
class ProviderCapabilities:
    """Capabilities of a provider."""

    supports_streaming: bool = True
    supports_tools: bool = False
    supports_vision: bool = False
    supports_thinking: bool = False
    supports_system_prompts: bool = True
    supports_temperature: bool = True
    supports_top_p: bool = True
    supports_stop_sequences: bool = True
    supports_json_mode: bool = False
    supports_grammar: bool = False
    max_batch_size: int = 1
    custom_capabilities: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All provider implementations must inherit from this class and implement
    the required methods.
    """

    def __init__(self, base_url: str, timeout: float = 30.0):
        """
        Initialize provider.

        Args:
            base_url: Base URL of the provider API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.provider_type: ProviderType = ProviderType.OPENAI_COMPATIBLE

    @abstractmethod
    async def detect(self) -> bool:
        """
        Detect if this provider is available at the configured URL.

        Returns:
            True if provider detected, False otherwise
        """
        pass

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        """
        List available models from the provider.

        Returns:
            List of ModelInfo objects
        """
        pass

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate a chat completion (non-streaming).

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stop: Stop sequences
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    async def stream_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stop: Stop sequences
            **kwargs: Additional provider-specific parameters

        Yields:
            Text chunks as they are generated
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """
        Get provider-specific capabilities.

        Returns:
            ProviderCapabilities object
        """
        pass

    def get_provider_type(self) -> ProviderType:
        """
        Get the type of this provider.

        Returns:
            ProviderType enum value
        """
        return self.provider_type

    def get_health_endpoint(self) -> str:
        """
        Get the health check endpoint for this provider.

        Returns:
            URL path for health check
        """
        return f"{self.base_url}/health"

    def normalize_model_name(self, model_name: str) -> str:
        """
        Normalize model name for consistency.

        Args:
            model_name: Raw model name

        Returns:
            Normalized model name
        """
        return model_name.strip().lower()

    async def test_connection(self) -> bool:
        """
        Test if connection to provider is working.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            return await self.detect()
        except Exception:
            return False

    def __repr__(self) -> str:
        """String representation of provider."""
        return f"{self.__class__.__name__}(base_url={self.base_url}, type={self.provider_type.value})"
