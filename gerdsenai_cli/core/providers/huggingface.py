"""
Hugging Face Text Generation Inference (TGI) provider implementation.

Supports HF's high-performance inference engine.
"""

import logging
from typing import Any, AsyncGenerator

import httpx

from .base import LLMProvider, ModelInfo, ProviderCapabilities, ProviderType

logger = logging.getLogger(__name__)


class HuggingFaceProvider(LLMProvider):
    """
    Hugging Face Text Generation Inference provider.

    Supports HF TGI's API with advanced features like grammar constraints.
    """

    def __init__(self, base_url: str = "http://localhost:8080", timeout: float = 30.0):
        """Initialize Hugging Face TGI provider."""
        super().__init__(base_url, timeout)
        self.provider_type = ProviderType.HUGGINGFACE_TGI

    async def detect(self) -> bool:
        """
        Detect if HF TGI is running.

        TGI has specific info endpoint.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Try TGI-specific endpoint
                response = await client.get(f"{self.base_url}/info")
                if response.status_code == 200:
                    data = response.json()
                    # Check for TGI-specific fields
                    return "model_id" in data or "model_dtype" in data
                return False
        except Exception:
            # Try health endpoint
            try:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
            except Exception as e:
                logger.debug(f"HF TGI detection failed: {e}")
                return False

    async def list_models(self) -> list[ModelInfo]:
        """
        Get info about the loaded model in TGI.

        TGI typically serves one model at a time.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/info")
                response.raise_for_status()

                data = response.json()

                model_info = ModelInfo(
                    name=data.get("model_id", "unknown"),
                    provider=ProviderType.HUGGINGFACE_TGI,
                    context_length=data.get("max_input_length"),
                    parameters={
                        "dtype": data.get("model_dtype"),
                        "device_type": data.get("model_device_type"),
                        "max_total_tokens": data.get("max_total_tokens"),
                        "max_batch_size": data.get("max_batch_total_tokens"),
                    },
                    is_loaded=True,
                )

                return [model_info]

        except Exception as e:
            logger.error(f"Failed to get HF TGI model info: {e}")
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
        Generate completion using HF TGI.

        Note: TGI uses /generate endpoint, not chat format.
        We convert messages to prompt text.
        """
        try:
            # Convert messages to text prompt
            prompt = self._messages_to_prompt(messages)

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                request_data = {
                    "inputs": prompt,
                    "parameters": {
                        "temperature": temperature,
                        "do_sample": temperature > 0,
                    },
                }

                if max_tokens:
                    request_data["parameters"]["max_new_tokens"] = max_tokens

                if stop:
                    request_data["parameters"]["stop"] = stop

                # Add TGI-specific parameters
                if kwargs:
                    request_data["parameters"].update(kwargs)

                response = await client.post(
                    f"{self.base_url}/generate", json=request_data
                )
                response.raise_for_status()

                data = response.json()
                return data.get("generated_text", "")

        except Exception as e:
            logger.error(f"HF TGI completion failed: {e}")
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
        Stream completion from HF TGI.

        Uses /generate_stream endpoint with SSE.
        """
        try:
            prompt = self._messages_to_prompt(messages)

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                request_data = {
                    "inputs": prompt,
                    "parameters": {
                        "temperature": temperature,
                        "do_sample": temperature > 0,
                    },
                }

                if max_tokens:
                    request_data["parameters"]["max_new_tokens"] = max_tokens

                if stop:
                    request_data["parameters"]["stop"] = stop

                if kwargs:
                    request_data["parameters"].update(kwargs)

                async with client.stream(
                    "POST", f"{self.base_url}/generate_stream", json=request_data
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            data_str = line[5:].strip()

                            try:
                                import json

                                data = json.loads(data_str)

                                # TGI returns token info
                                token = data.get("token", {})
                                text = token.get("text", "")

                                if text:
                                    yield text

                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"HF TGI streaming failed: {e}")
            raise

    def get_capabilities(self) -> ProviderCapabilities:
        """
        Get HF TGI capabilities.

        Returns:
            ProviderCapabilities with TGI features
        """
        return ProviderCapabilities(
            supports_streaming=True,
            supports_tools=False,
            supports_vision=False,  # Depends on model
            supports_thinking=False,
            supports_system_prompts=True,
            supports_temperature=True,
            supports_top_p=True,
            supports_stop_sequences=True,
            supports_json_mode=False,
            supports_grammar=True,  # TGI supports grammar-guided generation
            max_batch_size=16,
            custom_capabilities={
                "grammar_constraints": True,
                "watermarking": True,
                "flash_attention": True,
                "paged_attention": True,
            },
        )

    def _messages_to_prompt(self, messages: list[dict[str, str]]) -> str:
        """
        Convert chat messages to a text prompt.

        Args:
            messages: List of message dicts

        Returns:
            Formatted prompt text
        """
        prompt_parts = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")

        # Add final assistant prompt
        prompt_parts.append("Assistant:")

        return "\n\n".join(prompt_parts)
