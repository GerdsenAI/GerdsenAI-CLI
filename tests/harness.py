"""Shared verification harness for the agentic tool-loop.

This consolidates the near-identical fake LLM clients and ``Agent`` builders that
grew across the test suite into one well-documented place, and gives every test a
one-liner to drive the *real* agent loop end-to-end over a ``tmp_path`` project.

Two pieces:

- ``ScriptedLLMClient`` — a fake ``LLMClient`` driven by a pre-scripted sequence of
  ``ChatResult``s. ``chat_with_tools`` (the native tool-calling path the loop
  prefers) pops the next scripted result; ``chat`` / ``stream_chat`` back the
  CHAT-mode / legacy single-shot path. It advertises native tool support via
  ``get_capabilities`` so ``run_agent_loop`` auto-selects the native path with no
  monkeypatch.
- ``build_agent`` — constructs a real ``Agent`` over a ``tmp_path`` project wired to
  a fake client, with backups redirected under ``tmp_path`` (hermetic), LLM intent
  detection off (deterministic), and project context marked built so a turn doesn't
  depend on a filesystem scan.

Plus ``tool_call`` / ``final`` ChatResult builders and ``run_turn`` /
``run_turn_stream`` convenience drivers that report which tools actually executed
and how many files changed.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.core.agent import Agent
from gerdsenai_cli.core.file_editor import BackupManager, FileEditor
from gerdsenai_cli.core.llm_client import ChatMessage, ChatResult, ToolCall


@dataclass
class _Capabilities:
    """Minimal stand-in for ProviderCapabilities (only what the loop reads)."""

    supports_tools: bool = True


class ScriptedLLMClient:
    """A fake ``LLMClient`` returning a pre-scripted sequence of ``ChatResult``s.

    ``chat_with_tools`` pops the next scripted result (native tool-calling path),
    recording the conversation it was handed and the tool schemas it was offered so
    tests can assert on them. ``chat`` / ``stream_chat`` return ``chat_reply`` (the
    CHAT-mode / single-shot path). When the script is exhausted, ``chat_with_tools``
    raises — a test that scripts no tool turns is asserting the loop never calls it.
    """

    def __init__(
        self,
        script: list[ChatResult] | None = None,
        *,
        chat_reply: str = "single-shot answer",
        context_window: int = 8192,
    ) -> None:
        self._script = list(script or [])
        self.chat_reply = chat_reply
        self._context_window = context_window
        # Telemetry for assertions.
        self.chat_calls = 0
        self.tool_calls = 0
        self.stream_calls = 0
        self.last_messages: list[ChatMessage] | None = None
        self.last_tools: list[dict[str, Any]] | None = None

    async def chat_with_tools(
        self, messages: list[ChatMessage], tools: list[dict[str, Any]], **kw: Any
    ) -> ChatResult:
        self.tool_calls += 1
        self.last_messages = list(messages)
        self.last_tools = tools
        if not self._script:
            raise AssertionError(
                "ScriptedLLMClient.chat_with_tools called with an exhausted script "
                "(the loop made more tool round-trips than were scripted)."
            )
        return self._script.pop(0)

    async def chat(self, messages: list[ChatMessage], **kw: Any) -> str:
        self.chat_calls += 1
        self.last_messages = list(messages)
        return self.chat_reply

    async def stream_chat(
        self, messages: list[ChatMessage], **kw: Any
    ) -> AsyncIterator[str]:
        self.stream_calls += 1
        self.last_messages = list(messages)
        # Yield in two chunks to exercise accumulation.
        mid = max(1, len(self.chat_reply) // 2)
        yield self.chat_reply[:mid]
        yield self.chat_reply[mid:]

    def get_model_context_window(self, model_id: str) -> int:
        return self._context_window

    def get_capabilities(self) -> _Capabilities:
        return _Capabilities(supports_tools=True)


def build_agent(
    tmp_path: Path,
    client: Any,
    *,
    mode: str = "execute",
    preferences: dict[str, Any] | None = None,
) -> Agent:
    """Build a real ``Agent`` over ``tmp_path`` wired to a fake client.

    Args:
        tmp_path: project root (pytest fixture).
        client: a fake LLM client (typically ``ScriptedLLMClient``).
        mode: ``agent_mode`` — chat / architect / execute / llvl. The agent loop is
            enabled for every mode except ``chat`` (which pins the single-shot path).
        preferences: extra ``set_preference`` overrides applied last.

    Backups are redirected under ``tmp_path`` (hermetic), LLM intent detection is
    off (deterministic), and ``project_context_built`` is set so the turn doesn't
    depend on a filesystem scan.
    """
    settings = Settings()
    settings.set_preference("enable_llm_intent_detection", False)
    settings.set_preference("streaming", False)
    settings.set_preference("agent_mode", mode)
    settings.set_preference("enable_agent_loop", mode != "chat")
    for key, value in (preferences or {}).items():
        settings.set_preference(key, value)

    agent = Agent(client, settings, project_root=tmp_path)
    agent.file_editor = FileEditor(
        backup_manager=BackupManager(backup_dir=tmp_path / ".backups")
    )
    agent.conversation.project_context_built = True
    return agent


def tool_call(name: str, **arguments: Any) -> ChatResult:
    """A ``ChatResult`` that requests a single tool call."""
    return ChatResult(
        content="",
        tool_calls=[ToolCall(id=f"c_{name}", name=name, arguments=arguments)],
    )


def final(text: str, *, reasoning: str = "") -> ChatResult:
    """A ``ChatResult`` that is a final answer (no tool calls)."""
    return ChatResult(content=text, reasoning=reasoning)


@dataclass
class TurnResult:
    """Outcome of driving one user turn through the agent."""

    text: str
    tools_run: list[str] = field(default_factory=list)
    files_modified: int = 0


def _instrument(agent: Agent, record: list[str]) -> None:
    """Wrap each default-registry tool so executions append their name to ``record``."""
    registry = agent._get_tool_registry()
    for tool in registry.tools.values():
        original = tool.func

        async def wrapped(
            *a: Any, _orig: Any = original, _name: str = tool.name, **k: Any
        ) -> str:
            record.append(_name)
            return await _orig(*a, **k)

        tool.func = wrapped


async def run_turn(agent: Agent, text: str) -> TurnResult:
    """Drive ``process_user_input`` for one turn, reporting tools run + files changed."""
    record: list[str] = []
    _instrument(agent, record)
    before = agent.files_modified
    out = await agent.process_user_input(text)
    return TurnResult(
        text=out, tools_run=record, files_modified=agent.files_modified - before
    )


async def run_turn_stream(agent: Agent, text: str) -> TurnResult:
    """Drive ``process_user_input_stream`` for one turn, assembling the final text.

    Returns the concatenated ``kind == "text"`` chunks (the final answer), plus the
    tools that ran and the file-modification delta.
    """
    record: list[str] = []
    _instrument(agent, record)
    before = agent.files_modified
    text_out = ""
    async for chunk, _accumulated, kind in agent.process_user_input_stream(text):
        if kind == "text":
            text_out += chunk
    return TurnResult(
        text=text_out, tools_run=record, files_modified=agent.files_modified - before
    )
