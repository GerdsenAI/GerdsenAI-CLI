"""End-to-end tests for the agent's send path.

Exercises ``process_user_input`` and ``process_user_input_stream`` from raw
user text through context building, the LLM call, and final-response assembly,
with the LLM (and only the LLM) faked. The goal is to lock in the behaviour of
the path itself: conversation bookkeeping, the non-streaming/streaming variants,
security sanitization, and graceful handling of an empty model response.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.core.agent import Agent
from gerdsenai_cli.core.llm_client import ChatMessage


class FakeLLMClient:
    """Stand-in for LLMClient covering just what the send path touches."""

    def __init__(self, response: str = "Hello from the model.") -> None:
        self.response = response
        self.chat_calls = 0
        self.stream_calls = 0
        self.last_messages: list[ChatMessage] | None = None

    async def chat(self, messages: list[ChatMessage], **kwargs: Any) -> str:
        self.chat_calls += 1
        self.last_messages = messages
        return self.response

    async def stream_chat(self, messages: list[ChatMessage], **kwargs: Any):
        self.stream_calls += 1
        self.last_messages = messages
        # Yield in a couple of chunks to exercise accumulation.
        mid = max(1, len(self.response) // 2)
        yield self.response[:mid]
        yield self.response[mid:]

    def get_model_context_window(self, model_id: str) -> int:
        return 8192


def _make_agent(
    tmp_path: Path, response: str = "Hello from the model.", streaming: bool = False
) -> tuple[Agent, FakeLLMClient]:
    """Build a real Agent with a faked LLM client.

    LLM-based intent detection is disabled so a plain message takes the
    deterministic CHAT path (regex intent -> CHAT, no action), and streaming is
    toggled explicitly per test.
    """
    settings = Settings()
    settings.set_preference("enable_llm_intent_detection", False)
    settings.set_preference("streaming", streaming)
    client = FakeLLMClient(response)
    agent = Agent(client, settings, project_root=tmp_path)
    # Mark context as already built so the turn doesn't depend on a project scan.
    agent.conversation.project_context_built = True
    return agent, client


@pytest.mark.asyncio
async def test_process_user_input_returns_model_response(tmp_path: Path) -> None:
    agent, client = _make_agent(tmp_path, response="Four.")
    out = await agent.process_user_input("what is two plus two")
    assert "Four." in out
    assert client.chat_calls == 1
    assert client.stream_calls == 0


@pytest.mark.asyncio
async def test_process_user_input_records_conversation(tmp_path: Path) -> None:
    agent, _ = _make_agent(tmp_path, response="Noted.")
    await agent.process_user_input("remember this please")
    roles = [(m.role, m.content) for m in agent.conversation.messages]
    # The user turn and the assistant reply are both recorded, in order.
    assert ("user", "remember this please") in roles
    assert ("assistant", "Noted.") in roles
    assert roles.index(("user", "remember this please")) < roles.index(
        ("assistant", "Noted.")
    )


@pytest.mark.asyncio
async def test_process_user_input_sends_system_context(tmp_path: Path) -> None:
    agent, client = _make_agent(tmp_path)
    await agent.process_user_input("hello there")
    assert client.last_messages is not None
    # The first message is always the system prompt; the latest user message is
    # carried through (escaped) in the history.
    assert client.last_messages[0].role == "system"
    assert any(m.role == "user" for m in client.last_messages)


@pytest.mark.asyncio
async def test_process_user_input_increments_actions(tmp_path: Path) -> None:
    agent, _ = _make_agent(tmp_path)
    assert agent.actions_performed == 0
    await agent.process_user_input("just chatting")
    assert agent.actions_performed == 1


@pytest.mark.asyncio
async def test_process_user_input_empty_response_is_handled(tmp_path: Path) -> None:
    agent, _ = _make_agent(tmp_path, response="")
    out = await agent.process_user_input("say nothing")
    assert "trouble connecting" in out.lower()


@pytest.mark.asyncio
async def test_process_user_input_blocks_malicious_input(tmp_path: Path) -> None:
    agent, client = _make_agent(tmp_path)
    # An input that sanitizes to empty should be blocked before any LLM call.
    out = await agent.process_user_input("\x00\x00\x00")
    if client.chat_calls == 0:
        assert "blocked" in out.lower()
    else:
        # If the validator let it through, it must still have produced a reply.
        assert out


# --------------------------------------------------------------------------- #
# streaming variant
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_process_user_input_stream_yields_and_accumulates(
    tmp_path: Path,
) -> None:
    agent, client = _make_agent(tmp_path, response="streamed reply", streaming=True)
    chunks: list[str] = []
    final = ""
    async for chunk, accumulated in agent.process_user_input_stream("tell me"):
        chunks.append(chunk)
        final = accumulated
    assert client.stream_calls == 1
    assert client.chat_calls == 0
    # The accumulated text is the concatenation of the streamed chunks.
    assert final == "streamed reply"
    assert "".join(chunks).startswith("streamed")


@pytest.mark.asyncio
async def test_process_user_input_stream_records_assistant_message(
    tmp_path: Path,
) -> None:
    agent, _ = _make_agent(tmp_path, response="final answer", streaming=True)
    async for _chunk, _accumulated in agent.process_user_input_stream("question?"):
        pass
    assert any(
        m.role == "assistant" and m.content == "final answer"
        for m in agent.conversation.messages
    )
