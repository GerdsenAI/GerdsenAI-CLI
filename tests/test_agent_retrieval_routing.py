"""Tests for agent retrieval injection and per-persona provider routing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.core.agent import Agent
from gerdsenai_cli.core.llm_client import ChatMessage


class FakeLLMClient:
    """Minimal stand-in for LLMClient used by the agent's send path."""

    def __init__(self) -> None:
        self.chat_calls = 0
        self.stream_calls = 0

    async def chat(self, messages: list[ChatMessage], **kwargs: Any) -> str:
        self.chat_calls += 1
        return "local-response"

    async def stream_chat(self, messages: list[ChatMessage], **kwargs: Any):
        self.stream_calls += 1
        for chunk in ["local-", "stream"]:
            yield chunk


@pytest.fixture
def agent(tmp_path: Path) -> Agent:
    settings = Settings()
    return Agent(FakeLLMClient(), settings, project_root=tmp_path)


def _msgs() -> list[ChatMessage]:
    return [
        ChatMessage(role="system", content="sys"),
        ChatMessage(role="user", content="hi"),
    ]


# --------------------------------------------------------------------------- #
# provider routing
# --------------------------------------------------------------------------- #


def test_route_provider_none_by_default(agent: Agent) -> None:
    assert agent._route_provider() is None


def test_route_provider_none_for_local_persona(agent: Agent) -> None:
    agent.settings.agent_profiles = {"rev": {"model": "qwen", "provider": "ollama"}}
    agent.settings.active_agent_profile = "rev"
    assert agent._route_provider() is None


def test_route_provider_anthropic_persona(agent: Agent) -> None:
    agent.settings.agent_profiles = {
        "arch": {"model": "claude-opus-4-8", "provider": "anthropic"}
    }
    agent.settings.active_agent_profile = "arch"
    provider = agent._route_provider()
    assert provider is not None
    assert provider.__class__.__name__ == "AnthropicProvider"


def test_route_provider_claude_model_no_persona(agent: Agent) -> None:
    # Selecting a claude-* model directly routes to Anthropic, no persona needed.
    agent.settings.current_model = "claude-opus-4-8"
    provider = agent._route_provider()
    assert provider is not None
    assert provider.__class__.__name__ == "AnthropicProvider"
    assert provider.model == "claude-opus-4-8"


def test_route_provider_local_model_no_persona(agent: Agent) -> None:
    agent.settings.current_model = "qwen2.5-coder"
    assert agent._route_provider() is None


def test_to_dict_messages(agent: Agent) -> None:
    assert agent._to_dict_messages(_msgs()) == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]


@pytest.mark.asyncio
async def test_complete_response_uses_local_by_default(agent: Agent) -> None:
    out = await agent._complete_response(_msgs())
    assert out == "local-response"
    assert agent.llm_client.chat_calls == 1


@pytest.mark.asyncio
async def test_stream_response_uses_local_by_default(agent: Agent) -> None:
    chunks = [c async for c in agent._stream_response(_msgs())]
    assert "".join(chunks) == "local-stream"


class _FakeProvider:
    async def detect(self) -> bool:
        return True

    async def chat_completion(self, messages: Any, model: str, **kw: Any) -> str:
        return "claude-response"

    async def stream_completion(self, messages: Any, model: str, **kw: Any):
        for c in ["claude-", "stream"]:
            yield c


@pytest.mark.asyncio
async def test_complete_response_routes_to_provider(agent: Agent) -> None:
    agent._route_provider = lambda: _FakeProvider()  # type: ignore[method-assign]
    out = await agent._complete_response(_msgs())
    assert out == "claude-response"
    assert agent.llm_client.chat_calls == 0  # local not used


@pytest.mark.asyncio
async def test_stream_response_routes_to_provider(agent: Agent) -> None:
    agent._route_provider = lambda: _FakeProvider()  # type: ignore[method-assign]
    chunks = [c async for c in agent._stream_response(_msgs())]
    assert "".join(chunks) == "claude-stream"


@pytest.mark.asyncio
async def test_provider_fallback_when_undetected(agent: Agent) -> None:
    class _Undetected(_FakeProvider):
        async def detect(self) -> bool:
            return False

    agent._route_provider = lambda: _Undetected()  # type: ignore[method-assign]
    out = await agent._complete_response(_msgs())
    assert out == "local-response"  # fell back to local client


# --------------------------------------------------------------------------- #
# semantic retrieval injection
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_retrieve_semantic_disabled_by_default(agent: Agent) -> None:
    assert await agent._retrieve_semantic_context("anything") == ""


@pytest.mark.asyncio
async def test_retrieve_semantic_when_enabled(agent: Agent, monkeypatch: Any) -> None:
    agent.settings.enable_vector_index = True

    class _Hit:
        payload = {"path": "a.py", "start_line": 3, "text": "def foo(): ..."}

    class _Indexer:
        async def search(self, query: str, limit: int = 5) -> list[Any]:
            return [_Hit()]

        async def aclose(self) -> None:
            return None

    async def fake_build_indexer(settings: Any, root: Path) -> Any:
        return _Indexer()

    monkeypatch.setattr(
        "gerdsenai_cli.core.repo_index.build_indexer", fake_build_indexer
    )
    out = await agent._retrieve_semantic_context("foo")
    assert "a.py:3" in out
    assert "def foo()" in out


@pytest.mark.asyncio
async def test_retrieve_semantic_noop_when_no_indexer(
    agent: Agent, monkeypatch: Any
) -> None:
    agent.settings.enable_vector_index = True

    async def none_indexer(settings: Any, root: Path) -> Any:
        return None

    monkeypatch.setattr("gerdsenai_cli.core.repo_index.build_indexer", none_indexer)
    assert await agent._retrieve_semantic_context("foo") == ""


@pytest.mark.asyncio
async def test_retrieve_semantic_closes_indexer(agent: Agent, monkeypatch: Any) -> None:
    """The per-search indexer's pooled connection is released (no socket leak)."""
    agent.settings.enable_vector_index = True
    closed = {"n": 0}

    class _Indexer:
        async def search(self, query: str, limit: int = 5) -> list[Any]:
            return []

        async def aclose(self) -> None:
            closed["n"] += 1

    async def fake_build_indexer(settings: Any, root: Path) -> Any:
        return _Indexer()

    monkeypatch.setattr(
        "gerdsenai_cli.core.repo_index.build_indexer", fake_build_indexer
    )
    await agent._retrieve_semantic_context("foo")
    assert closed["n"] == 1


@pytest.mark.asyncio
async def test_retrieve_semantic_closes_indexer_on_search_error(
    agent: Agent, monkeypatch: Any
) -> None:
    """Even when search raises, the indexer is still closed (finally)."""
    agent.settings.enable_vector_index = True
    closed = {"n": 0}

    class _Indexer:
        async def search(self, query: str, limit: int = 5) -> list[Any]:
            raise RuntimeError("qdrant blew up")

        async def aclose(self) -> None:
            closed["n"] += 1

    async def fake_build_indexer(settings: Any, root: Path) -> Any:
        return _Indexer()

    monkeypatch.setattr(
        "gerdsenai_cli.core.repo_index.build_indexer", fake_build_indexer
    )
    out = await agent._retrieve_semantic_context("foo")
    assert out == ""  # graceful degradation preserved
    assert closed["n"] == 1  # and still closed
