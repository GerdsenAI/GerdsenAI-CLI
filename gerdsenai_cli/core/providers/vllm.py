"""
vLLM provider implementation.

vLLM uses OpenAI-compatible API with additional features.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from .base import LLMProvider, ModelInfo, ProviderCapabilities, ProviderType

logger = logging.getLogger(__name__)


class VLLMProvider(LLMProvider):
    """
    vLLM provider implementation.

    vLLM is a high-throughput and memory-efficient inference engine
    with OpenAI-compatible API.
    """

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 30.0):
        """Initialize vLLM provider."""
        super().__init__(base_url, timeout)
        self.provider_type = ProviderType.VLLM

    async def detect(self) -> bool:
        """
        Detect if vLLM is running.

        vLLM typically responds to /v1/models endpoint.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Try OpenAI-compatible endpoint
                response = await client.get(f"{self.base_url}/v1/models")
                if response.status_code == 200:
                    # Check if response looks like vLLM
                    data = response.json()
                    # vLLM typically has fewer fields than real OpenAI
                    return "data" in data
                return False
        except Exception as e:
            logger.debug(f"vLLM detection failed: {e}")
            return False

    async def list_models(self) -> list[ModelInfo]:
        """
        List models available in vLLM.

        Returns:
            List of ModelInfo objects
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/v1/models")
                response.raise_for_status()

                data = response.json()
                models = []

                for model_data in data.get("data", []):
                    model_info = ModelInfo(
                        name=model_data.get("id", ""),
                        provider=ProviderType.VLLM,
                        context_length=model_data.get("max_model_len"),
                        parameters={
                            "owned_by": model_data.get("owned_by"),
                            "created": model_data.get("created"),
                        },
                        is_loaded=True,  # vLLM loads models at startup
                    )
                    models.append(model_info)

                return models

        except Exception as e:
            logger.error(f"Failed to list vLLM models: {e}")
            return []

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
        Generate chat completion using vLLM.

        Uses OpenAI-compatible format.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                request_data = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": False,
                }

                if max_tokens:
                    request_data["max_tokens"] = max_tokens

                if stop:
                    request_data["stop"] = stop

                # Add vLLM-specific parameters
                if kwargs:
                    request_data.update(kwargs)

                response = await client.post(
                    f"{self.base_url}/v1/chat/completions", json=request_data
                )
                response.raise_for_status()

                data = response.json()
                return data["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"vLLM chat completion failed: {e}")
            raise

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
        Stream chat completion from vLLM.

        Uses OpenAI-compatible SSE format.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                request_data = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": True,
                }

                if max_tokens:
                    request_data["max_tokens"] = max_tokens

                if stop:
                    request_data["stop"] = stop

                if kwargs:
                    request_data.update(kwargs)

                async with client.stream(
                    "POST", f"{self.base_url}/v1/chat/completions", json=request_data
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            if data_str.strip() == "[DONE]":
                                break

                            try:
                                import json

                                data = json.loads(data_str)
                                delta = data["choices"][0]["delta"]
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"vLLM streaming failed: {e}")
            raise

    def get_capabilities(self) -> ProviderCapabilities:
        """
        Get vLLM capabilities.

        Returns:
            ProviderCapabilities with vLLM features
        """
        return ProviderCapabilities(
            supports_streaming=True,
            supports_tools=False,  # vLLM doesn't have built-in tool calling
            supports_vision=False,  # Depends on model
            supports_thinking=False,
            supports_system_prompts=True,
            supports_temperature=True,
            supports_top_p=True,
            supports_stop_sequences=True,
            supports_json_mode=False,
            supports_grammar=True,  # vLLM supports grammar-based generation
            max_batch_size=32,  # vLLM supports batching
            custom_capabilities={
                "tensor_parallel": True,
                "lora_adapters": True,
                "continuous_batching": True,
                "prefix_caching": True,
            },
        )
