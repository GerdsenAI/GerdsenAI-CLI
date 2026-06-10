"""PR 2b-3: the agent loop streams through process_user_input_stream.

Before this, the streaming path (what the TUI uses by default) bypassed the
agent loop entirely — only the non-streaming process_user_input ran it. These
tests prove the loop now drives the streamed turn and surfaces its tool-call /
reasoning / final-answer events as (chunk, accumulated, kind) tuples.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.core.agent import Agent
from gerdsenai_cli.core.file_editor import BackupManager, FileEditor
from gerdsenai_cli.core.llm_client import ChatMessage, ChatResult, ToolCall


class ScriptedToolClient:
    """Fake LLM client returning a scripted ChatResult sequence (native path)."""

    def __init__(self, script: list[ChatResult]) -> None:
        self._script = list(script)

    async def chat_with_tools(
        self, messages: list[ChatMessage], tools: list[dict[str, Any]], **kw: Any
    ) -> ChatResult:
        return self._script.pop(0)

    async def chat(self, messages: list[ChatMessage], **kw: Any) -> str:
        return "single-shot answer"

    async def stream_chat(self, messages: list[ChatMessage], **kw: Any):
        yield "single-shot answer"

    def get_model_context_window(self, model_id: str) -> int:
        return 8192


@pytest.fixture(autouse=True)
def _force_native_tools(monkeypatch: Any) -> None:
    import gerdsenai_cli.core.tool_registry as tr

    async def _native(_client: Any) -> bool:
        return True

    monkeypatch.setattr(tr, "_supports_native_tools", _native)


def _agent(tmp_path: Path, client: Any, mode: str = "execute") -> Agent:
    settings = Settings()
    settings.set_preference("enable_llm_intent_detection", False)
    settings.set_preference("agent_mode", mode)
    agent = Agent(client, settings, project_root=tmp_path)
    agent.file_editor = FileEditor(
        backup_manager=BackupManager(backup_dir=tmp_path / ".backups")
    )
    agent.conversation.project_context_built = True
    return agent


def _call(name: str, **args: Any) -> ChatResult:
    return ChatResult(
        content="", tool_calls=[ToolCall(id=f"c_{name}", name=name, arguments=args)]
    )


async def _drain(agent: Agent, text: str) -> list[tuple[str, str, str]]:
    return [t async for t in agent.process_user_input_stream(text)]


@pytest.mark.asyncio
async def test_stream_runs_the_loop_and_emits_tool_then_text(tmp_path: Path) -> None:
    """A read->final loop streams a 'tool' event then the 'text' answer."""
    target = tmp_path / "a.py"
    target.write_text("x = 1\n")
    client = ScriptedToolClient(
        [
            _call("read_file", path=str(target)),
            ChatResult(content="The file sets x to 1."),
        ]
    )
    agent = _agent(tmp_path, client, mode="execute")

    events = await _drain(agent, "what does a.py do")
    kinds = [k for _c, _a, k in events]
    text = "".join(c for c, _a, k in events if k == "text")

    assert "tool" in kinds  # the read_file call surfaced as a status line
    assert "The file sets x to 1." in text
    # A tool status line mentions the tool name.
    assert any("read_file" in c for c, _a, k in events if k == "tool")


@pytest.mark.asyncio
async def test_stream_surfaces_reasoning_kind(tmp_path: Path) -> None:
    client = ScriptedToolClient(
        [ChatResult(content="done", reasoning="I should just answer directly.")]
    )
    agent = _agent(tmp_path, client, mode="execute")

    events = await _drain(agent, "hi")
    reasoning = "".join(c for c, _a, k in events if k == "reasoning")
    text = "".join(c for c, _a, k in events if k == "text")
    assert "answer directly" in reasoning
    assert "done" in text


@pytest.mark.asyncio
async def test_stream_records_assistant_answer_only(tmp_path: Path) -> None:
    """Only the final answer text is stored to history (not reasoning/tool noise)."""
    client = ScriptedToolClient(
        [ChatResult(content="final answer", reasoning="some thinking")]
    )
    agent = _agent(tmp_path, client, mode="execute")
    await _drain(agent, "q")
    assistant = [
        m.content for m in agent.conversation.messages if m.role == "assistant"
    ]
    assert assistant == ["final answer"]


@pytest.mark.asyncio
async def test_chat_mode_stream_skips_the_loop(tmp_path: Path) -> None:
    """CHAT mode keeps the legacy single-shot stream (loop inactive)."""
    client = ScriptedToolClient([])  # chat_with_tools must never be called
    agent = _agent(tmp_path, client, mode="chat")
    events = await _drain(agent, "just chatting")
    text = "".join(c for c, _a, k in events if k == "text")
    assert text == "single-shot answer"
    # All chunks from the legacy path are "text".
    assert all(k == "text" for _c, _a, k in events)


@pytest.mark.asyncio
async def test_every_event_is_a_three_tuple(tmp_path: Path) -> None:
    client = ScriptedToolClient(
        [_call("read_file", path="a.py"), ChatResult(content="ok")]
    )
    agent = _agent(tmp_path, client, mode="execute")
    async for event in agent.process_user_input_stream("go"):
        assert len(event) == 3
        chunk, accumulated, kind = event
        assert isinstance(chunk, str)
        assert isinstance(accumulated, str)
        assert kind in {"text", "reasoning", "tool"}
