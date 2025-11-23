"""
LM Studio provider implementation.

LM Studio uses OpenAI-compatible API for local GGUF models.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from .base import LLMProvider, ModelInfo, ProviderCapabilities, ProviderType

logger = logging.getLogger(__name__)


class LMStudioProvider(LLMProvider):
    """
    LM Studio provider implementation.

    LM Studio provides a user-friendly interface for running GGUF models
    locally with an OpenAI-compatible API.
    """

    def __init__(self, base_url: str = "http://localhost:1234", timeout: float = 30.0):
        """Initialize LM Studio provider."""
        super().__init__(base_url, timeout)
        self.provider_type = ProviderType.LM_STUDIO

    async def detect(self) -> bool:
        """
        Detect if LM Studio is running.

        LM Studio typically runs on port 1234.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/v1/models")
                if response.status_code == 200:
                    data = response.json()
                    # LM Studio has specific metadata
                    return "data" in data and "object" in data
                return False
        except Exception as e:
            logger.debug(f"LM Studio detection failed: {e}")
            return False

    async def list_models(self) -> list[ModelInfo]:
        """
        List models loaded in LM Studio.

        Returns:
            List of currently loaded models
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/v1/models")
                response.raise_for_status()

                data = response.json()
                models = []

                for model_data in data.get("data", []):
                    model_name = model_data.get("id", "")

                    model_info = ModelInfo(
                        name=model_name,
                        provider=ProviderType.LM_STUDIO,
                        quantization=self._extract_quantization(model_name),
                        parameters={
                            "owned_by": model_data.get("owned_by", "lm-studio"),
                            "created": model_data.get("created"),
                        },
                        is_loaded=True,
                    )
                    models.append(model_info)

                return models

        except Exception as e:
            logger.error(f"Failed to list LM Studio models: {e}")
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
        Generate chat completion using LM Studio.

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

                if kwargs:
                    request_data.update(kwargs)

                response = await client.post(
                    f"{self.base_url}/v1/chat/completions", json=request_data
                )
                response.raise_for_status()

                data = response.json()
                return data["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"LM Studio chat completion failed: {e}")
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
        Stream chat completion from LM Studio.

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
                            data_str = line[6:]
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
            logger.error(f"LM Studio streaming failed: {e}")
            raise

    def get_capabilities(self) -> ProviderCapabilities:
        """
        Get LM Studio capabilities.

        Returns:
            ProviderCapabilities for LM Studio
        """
        return ProviderCapabilities(
            supports_streaming=True,
            supports_tools=False,
            supports_vision=False,  # GGUF models typically text-only
            supports_thinking=False,
            supports_system_prompts=True,
            supports_temperature=True,
            supports_top_p=True,
            supports_stop_sequences=True,
            supports_json_mode=False,
            supports_grammar=False,
            max_batch_size=1,
            custom_capabilities={
                "gguf_quantization": True,
                "gpu_layers": True,  # LM Studio supports partial GPU offloading
                "rope_frequency_scaling": True,
            },
        )

    def _extract_quantization(self, model_name: str) -> str | None:
        """
        Extract quantization from GGUF model name.

        Args:
            model_name: Model name (e.g., "llama-2-7b-chat.Q4_K_M.gguf")

        Returns:
            Quantization level or None
        """
        import re

        # Match GGUF quantization patterns
        patterns = [
            r"Q(\d+)_([KMS]_?[MS]?)",  # Q4_K_M, Q5_K_S, etc.
            r"q(\d+)_(\d+)",  # q4_0, q5_1
        ]

        for pattern in patterns:
            match = re.search(pattern, model_name, re.IGNORECASE)
            if match:
                return match.group(0).upper()

        return None
