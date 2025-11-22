"""
Ollama provider implementation.

Ollama-specific API client with native format support.
"""

import logging
from typing import Any, AsyncGenerator

import httpx

from .base import LLMProvider, ModelInfo, ProviderCapabilities, ProviderType

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """
    Ollama-specific provider implementation.

    Supports Ollama's native API format with model management capabilities.
    """

    def __init__(self, base_url: str = "http://localhost:11434", timeout: float = 30.0):
        """Initialize Ollama provider."""
        super().__init__(base_url, timeout)
        self.provider_type = ProviderType.OLLAMA

    async def detect(self) -> bool:
        """
        Detect if Ollama is running.

        Checks for Ollama-specific endpoints.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Try Ollama-specific endpoint
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama detection failed: {e}")
            return False

    async def list_models(self) -> list[ModelInfo]:
        """
        List models available in Ollama.

        Returns:
            List of ModelInfo objects with Ollama-specific details
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()

                data = response.json()
                models = []

                for model_data in data.get("models", []):
                    model_info = ModelInfo(
                        name=model_data.get("name", ""),
                        provider=ProviderType.OLLAMA,
                        size=model_data.get("size"),
                        quantization=self._extract_quantization(
                            model_data.get("name", "")
                        ),
                        context_length=model_data.get("details", {}).get(
                            "context_length"
                        ),
                        parameters={
                            "family": model_data.get("details", {}).get("family"),
                            "parameter_size": model_data.get("details", {}).get(
                                "parameter_size"
                            ),
                            "quantization_level": model_data.get("details", {}).get(
                                "quantization_level"
                            ),
                        },
                        is_loaded=True,  # Ollama keeps models loaded
                    )
                    models.append(model_info)

                return models

        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
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
        Generate chat completion using Ollama.

        Args:
            messages: Chat messages
            model: Model name
            temperature: Sampling temperature
            max_tokens: Max tokens (num_predict in Ollama)
            stop: Stop sequences
            **kwargs: Additional Ollama options

        Returns:
            Generated response text
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Ollama-specific format
                request_data = {
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                    },
                }

                if max_tokens:
                    request_data["options"]["num_predict"] = max_tokens

                if stop:
                    request_data["options"]["stop"] = stop

                # Merge additional options
                if kwargs:
                    request_data["options"].update(kwargs)

                response = await client.post(
                    f"{self.base_url}/api/chat", json=request_data
                )
                response.raise_for_status()

                data = response.json()
                return data.get("message", {}).get("content", "")

        except Exception as e:
            logger.error(f"Ollama chat completion failed: {e}")
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
        Stream chat completion from Ollama.

        Args:
            messages: Chat messages
            model: Model name
            temperature: Sampling temperature
            max_tokens: Max tokens
            stop: Stop sequences
            **kwargs: Additional options

        Yields:
            Text chunks
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                request_data = {
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                    },
                }

                if max_tokens:
                    request_data["options"]["num_predict"] = max_tokens

                if stop:
                    request_data["options"]["stop"] = stop

                if kwargs:
                    request_data["options"].update(kwargs)

                async with client.stream(
                    "POST", f"{self.base_url}/api/chat", json=request_data
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line:
                            try:
                                import json

                                data = json.loads(line)
                                content = data.get("message", {}).get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}")
            raise

    def get_capabilities(self) -> ProviderCapabilities:
        """
        Get Ollama capabilities.

        Returns:
            ProviderCapabilities with Ollama-specific features
        """
        return ProviderCapabilities(
            supports_streaming=True,
            supports_tools=False,  # Ollama doesn't have native tool calling yet
            supports_vision=True,  # Some Ollama models support vision
            supports_thinking=False,
            supports_system_prompts=True,
            supports_temperature=True,
            supports_top_p=True,
            supports_stop_sequences=True,
            supports_json_mode=True,  # Ollama supports JSON format
            supports_grammar=False,
            max_batch_size=1,
            custom_capabilities={
                "model_pull": True,
                "model_delete": True,
                "embeddings": True,
                "model_info": True,
            },
        )

    def _extract_quantization(self, model_name: str) -> str | None:
        """
        Extract quantization from model name.

        Args:
            model_name: Ollama model name (e.g., "llama2:7b-q4_0")

        Returns:
            Quantization level or None
        """
        parts = model_name.split(":")
        if len(parts) > 1:
            tag = parts[1]
            # Extract quantization (q4_0, q5_k_m, etc.)
            import re

            match = re.search(r"q\d+_[\w]+", tag, re.IGNORECASE)
            if match:
                return match.group(0).upper()
        return None

    async def pull_model(self, model_name: str) -> AsyncGenerator[dict, None]:
        """
        Pull/download a model in Ollama.

        Args:
            model_name: Name of model to pull

        Yields:
            Progress updates
        """
        try:
            async with httpx.AsyncClient(
                timeout=None
            ) as client:  # No timeout for downloads
                async with client.stream(
                    "POST", f"{self.base_url}/api/pull", json={"name": model_name}
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line:
                            try:
                                import json

                                yield json.loads(line)
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"Model pull failed: {e}")
            raise

    async def delete_model(self, model_name: str) -> bool:
        """
        Delete a model from Ollama.

        Args:
            model_name: Name of model to delete

        Returns:
            True if successful
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.base_url}/api/delete", json={"name": model_name}
                )
                response.raise_for_status()
                return True

        except Exception as e:
            logger.error(f"Model deletion failed: {e}")
            return False

    async def get_model_info(self, model_name: str) -> dict | None:
        """
        Get detailed information about a model.

        Args:
            model_name: Model name

        Returns:
            Model information dict or None
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/show", json={"name": model_name}
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Get model info failed: {e}")
            return None
