"""Anthropic (Claude) provider.

Optional, cloud-based provider for the Claude API. Local providers remain the
default; this one is only available when the ``anthropic`` SDK is installed and
an API key is present (OS keyring or the ``ANTHROPIC_API_KEY`` env var — never
``config.json``).

Implements prompt caching (``cache_control`` on the system prompt) and
streaming. Sampling parameters (``temperature``) are omitted for models that
reject them (Opus 4.7 / 4.8).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from ..secrets import get_secret
from .base import LLMProvider, ModelInfo, ProviderCapabilities, ProviderType

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-4-8"


def _to_anthropic_tool(tool: dict[str, Any]) -> dict[str, Any]:
    """Convert an OpenAI-shape tool schema to Anthropic's tool format.

    OpenAI: ``{"type": "function", "function": {"name", "description",
    "parameters"}}``. Anthropic: ``{"name", "description", "input_schema"}``.
    Already-Anthropic dicts (have ``input_schema``) pass through.
    """
    if "input_schema" in tool:
        return tool
    fn = tool.get("function", tool)
    return {
        "name": fn.get("name", ""),
        "description": fn.get("description", ""),
        "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
    }


# Known models and their context windows (cached; live list via the Models API
# when reachable). Source: Anthropic models overview.
KNOWN_MODELS: dict[str, int] = {
    "claude-opus-4-8": 1_000_000,
    "claude-opus-4-7": 1_000_000,
    "claude-opus-4-6": 1_000_000,
    "claude-sonnet-4-6": 1_000_000,
    "claude-haiku-4-5": 200_000,
}

# Models that reject temperature / top_p / top_k (return 400).
_NO_SAMPLING_PREFIXES = ("claude-opus-4-7", "claude-opus-4-8")


def _supports_temperature(model: str) -> bool:
    return not model.startswith(_NO_SAMPLING_PREFIXES)


class AnthropicProvider(LLMProvider):
    """Provider backed by the Anthropic Claude API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        timeout: float = 600.0,
    ) -> None:
        super().__init__("https://api.anthropic.com", timeout)
        self.provider_type = ProviderType.ANTHROPIC
        self._explicit_key = api_key
        self.model = model

    # -- helpers --------------------------------------------------------- #

    def _api_key(self) -> str | None:
        return self._explicit_key or get_secret("anthropic")

    def _client(self) -> Any:
        """Build an AsyncAnthropic client, or raise a clear error."""
        try:
            import anthropic
        except ImportError as e:
            raise RuntimeError(
                "The 'anthropic' package is not installed. "
                'Install it with: pip install "gerdsenai-cli[anthropic]"'
            ) from e

        key = self._api_key()
        if not key:
            raise RuntimeError(
                "No Anthropic API key found. Set one with `/anthropic set-key <key>` "
                "or the ANTHROPIC_API_KEY environment variable."
            )
        return anthropic.AsyncAnthropic(api_key=key, timeout=self.timeout)

    @staticmethod
    def _split_messages(
        messages: list[dict[str, str]],
    ) -> tuple[str, list[dict[str, str]]]:
        """Separate system text from the user/assistant turns."""
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        turns = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m.get("role") != "system"
        ]
        return "\n\n".join(system_parts), turns

    def _build_kwargs(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int | None,
        stop: list[str] | None,
    ) -> dict[str, Any]:
        system, turns = self._split_messages(messages)
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens or 4096,
            "messages": turns,
        }
        if system:
            # cache_control caches the stable system prefix across requests.
            kwargs["system"] = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        if stop:
            kwargs["stop_sequences"] = stop
        if _supports_temperature(model):
            kwargs["temperature"] = temperature
        return kwargs

    # -- interface ------------------------------------------------------- #

    async def detect(self) -> bool:
        """Available when the SDK is importable and a key is present."""
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False
        return self._api_key() is not None

    async def list_models(self) -> list[ModelInfo]:
        models: list[ModelInfo] = []
        # Try the live Models API; fall back to the known list.
        try:
            client = self._client()
            async for m in client.models.list():
                ctx = KNOWN_MODELS.get(m.id)
                models.append(
                    ModelInfo(
                        name=m.id,
                        provider=ProviderType.ANTHROPIC,
                        context_length=ctx,
                    )
                )
        except Exception as e:
            logger.debug(f"Live Anthropic model list failed, using known list: {e}")

        if not models:
            models = [
                ModelInfo(
                    name=name,
                    provider=ProviderType.ANTHROPIC,
                    context_length=ctx,
                )
                for name, ctx in KNOWN_MODELS.items()
            ]
        return models

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> str:
        client = self._client()
        params = self._build_kwargs(messages, model, temperature, max_tokens, stop)
        response = await client.messages.create(**params)
        return "".join(block.text for block in response.content if block.type == "text")

    async def stream_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        client = self._client()
        params = self._build_kwargs(messages, model, temperature, max_tokens, stop)
        async with client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                yield text

    async def chat_with_tools(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> Any:
        """Tool-aware completion using Claude's native ``tool_use`` blocks.

        Accepts OpenAI-shape tool schemas (the app's internal lingua franca),
        converts them to Anthropic's format, and parses ``tool_use`` blocks back
        into the provider-agnostic ChatResult used by the agent loop.
        """
        from ..llm_client import ChatResult, ToolCall

        client = self._client()
        params = self._build_kwargs(messages, model, temperature, max_tokens, None)
        params["tools"] = [_to_anthropic_tool(t) for t in tools]
        response = await client.messages.create(**params)

        content = "".join(
            block.text for block in response.content if block.type == "text"
        )
        tool_calls = [
            ToolCall(id=block.id, name=block.name, arguments=dict(block.input))
            for block in response.content
            if block.type == "tool_use"
        ]
        return ChatResult(content=content, tool_calls=tool_calls)

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
            supports_thinking=True,
            supports_system_prompts=True,
            supports_temperature=True,  # provider-wide; per-model handled internally
            supports_stop_sequences=True,
            supports_json_mode=True,
            custom_capabilities={"prompt_caching": True, "cloud": True},
        )
