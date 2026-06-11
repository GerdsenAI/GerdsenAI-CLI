"""PR 2b-3: the agent loop streams through process_user_input_stream.

Before this, the streaming path (what the TUI uses by default) bypassed the
agent loop entirely — only the non-streaming process_user_input ran it. These
tests prove the loop now drives the streamed turn and surfaces its tool-call /
reasoning / final-answer events as (chunk, accumulated, kind) tuples.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gerdsenai_cli.core.agent import Agent
from gerdsenai_cli.core.llm_client import ChatResult
from tests.harness import ScriptedLLMClient, build_agent
from tests.harness import tool_call as _call


async def _drain(agent: Agent, text: str) -> list[tuple[str, str, str]]:
    return [t async for t in agent.process_user_input_stream(text)]


@pytest.mark.asyncio
async def test_stream_runs_the_loop_and_emits_tool_then_text(tmp_path: Path) -> None:
    """A read->final loop streams a 'tool' event then the 'text' answer."""
    target = tmp_path / "a.py"
    target.write_text("x = 1\n")
    client = ScriptedLLMClient(
        [
            _call("read_file", path=str(target)),
            ChatResult(content="The file sets x to 1."),
        ]
    )
    agent = build_agent(tmp_path, client, mode="execute")

    events = await _drain(agent, "what does a.py do")
    kinds = [k for _c, _a, k in events]
    text = "".join(c for c, _a, k in events if k == "text")

    assert "tool" in kinds  # the read_file call surfaced as a status line
    assert "The file sets x to 1." in text
    # A tool status line mentions the tool name.
    assert any("read_file" in c for c, _a, k in events if k == "tool")


@pytest.mark.asyncio
async def test_stream_surfaces_reasoning_kind(tmp_path: Path) -> None:
    client = ScriptedLLMClient(
        [ChatResult(content="done", reasoning="I should just answer directly.")]
    )
    agent = build_agent(tmp_path, client, mode="execute")

    events = await _drain(agent, "hi")
    reasoning = "".join(c for c, _a, k in events if k == "reasoning")
    text = "".join(c for c, _a, k in events if k == "text")
    assert "answer directly" in reasoning
    assert "done" in text


@pytest.mark.asyncio
async def test_stream_records_assistant_answer_only(tmp_path: Path) -> None:
    """Only the final answer text is stored to history (not reasoning/tool noise)."""
    client = ScriptedLLMClient(
        [ChatResult(content="final answer", reasoning="some thinking")]
    )
    agent = build_agent(tmp_path, client, mode="execute")
    await _drain(agent, "q")
    assistant = [
        m.content for m in agent.conversation.messages if m.role == "assistant"
    ]
    assert assistant == ["final answer"]


@pytest.mark.asyncio
async def test_chat_mode_stream_skips_the_loop(tmp_path: Path) -> None:
    """CHAT mode keeps the legacy single-shot stream (loop inactive)."""
    client = ScriptedLLMClient([])  # chat_with_tools must never be called
    agent = build_agent(tmp_path, client, mode="chat")
    events = await _drain(agent, "just chatting")
    text = "".join(c for c, _a, k in events if k == "text")
    assert text == "single-shot answer"
    # All chunks from the legacy path are "text".
    assert all(k == "text" for _c, _a, k in events)


@pytest.mark.asyncio
async def test_every_event_is_a_three_tuple(tmp_path: Path) -> None:
    client = ScriptedLLMClient(
        [_call("read_file", path="a.py"), ChatResult(content="ok")]
    )
    agent = build_agent(tmp_path, client, mode="execute")
    async for event in agent.process_user_input_stream("go"):
        assert len(event) == 3
        chunk, accumulated, kind = event
        assert isinstance(chunk, str)
        assert isinstance(accumulated, str)
        assert kind in {"text", "reasoning", "tool"}
