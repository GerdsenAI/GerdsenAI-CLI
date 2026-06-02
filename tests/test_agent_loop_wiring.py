"""PR 2b-2: the agentic loop wired into Agent.process_user_input.

Proves the agent can now chain tool calls within ONE user turn (read -> edit ->
final, editing a real file on disk), that ExecutionMode gates autonomy
(CHAT = no tools; run_command always confirms outside LLVL), and that
enable_agent_loop=False restores the legacy single-shot path.
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
    """Fake LLM client returning a scripted sequence of ChatResults (native path)."""

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
    """Make the loop use the native chat_with_tools path (ScriptedToolClient).

    Uses monkeypatch so the module-global override is auto-reverted after each
    test (no cross-test leakage).
    """
    import gerdsenai_cli.core.tool_registry as tr

    async def _native(_client: Any) -> bool:
        return True

    monkeypatch.setattr(tr, "_supports_native_tools", _native)


def _agent(tmp_path: Path, client: Any, mode: str = "execute") -> Agent:
    settings = Settings()
    settings.set_preference("enable_llm_intent_detection", False)
    settings.set_preference("streaming", False)
    settings.set_preference("agent_mode", mode)
    agent = Agent(client, settings, project_root=tmp_path)
    # Hermetic backups under tmp_path.
    agent.file_editor = FileEditor(
        backup_manager=BackupManager(backup_dir=tmp_path / ".backups")
    )
    agent.conversation.project_context_built = True
    return agent


def _call(name: str, **args: Any) -> ChatResult:
    return ChatResult(
        content="", tool_calls=[ToolCall(id=f"c_{name}", name=name, arguments=args)]
    )


def _final(text: str) -> ChatResult:
    return ChatResult(content=text)


@pytest.mark.asyncio
async def test_read_then_edit_in_one_turn(tmp_path: Path) -> None:
    """The agent reads a file then edits it, on disk, within one user turn."""
    target = tmp_path / "hello.py"
    target.write_text("print('old')\n")

    client = ScriptedToolClient(
        [
            _call("read_file", path=str(target)),
            _call("edit_file", path=str(target), new_content="print('new')\n"),
            _final("Updated hello.py to print 'new'."),
        ]
    )
    agent = _agent(tmp_path, client, mode="execute")

    out = await agent.process_user_input("make hello.py print new")

    assert "Updated hello.py" in out
    assert target.read_text() == "print('new')\n"  # the edit hit disk


@pytest.mark.asyncio
async def test_chat_mode_does_not_use_tools(tmp_path: Path) -> None:
    """CHAT mode bypasses the loop: a single plain completion, no tools."""
    client = ScriptedToolClient([])  # chat_with_tools must never be called
    agent = _agent(tmp_path, client, mode="chat")

    out = await agent.process_user_input("just chatting")
    assert out == "single-shot answer"


@pytest.mark.asyncio
async def test_run_command_confirms_even_in_execute_mode(tmp_path: Path) -> None:
    """EXECUTE auto-allows edits, but run_command must still hit the confirm gate."""
    seen: list[str] = []

    client = ScriptedToolClient(
        [_call("run_command", command="rm -rf /"), _final("done")]
    )
    agent = _agent(tmp_path, client, mode="execute")

    async def confirm(name: str, args: dict[str, Any]) -> bool:
        seen.append(name)
        return False  # deny it

    agent.confirmation_callback = confirm
    await agent.process_user_input("delete everything")

    # run_command was routed through confirm despite EXECUTE mode.
    assert seen == ["run_command"]


@pytest.mark.asyncio
async def test_execute_mode_auto_allows_edits(tmp_path: Path) -> None:
    """In EXECUTE mode, file edits do NOT hit the confirm callback."""
    target = tmp_path / "f.py"
    target.write_text("x = 1\n")
    seen: list[str] = []

    client = ScriptedToolClient(
        [_call("edit_file", path=str(target), new_content="x = 2\n"), _final("ok")]
    )
    agent = _agent(tmp_path, client, mode="execute")

    async def confirm(name: str, args: dict[str, Any]) -> bool:
        seen.append(name)
        return True

    agent.confirmation_callback = confirm
    await agent.process_user_input("set x to 2")

    assert seen == []  # edit auto-allowed in EXECUTE
    assert target.read_text() == "x = 2\n"


@pytest.mark.asyncio
async def test_architect_mode_confirms_every_mutation(tmp_path: Path) -> None:
    target = tmp_path / "f.py"
    target.write_text("x = 1\n")
    seen: list[str] = []

    client = ScriptedToolClient(
        [_call("edit_file", path=str(target), new_content="x = 9\n"), _final("done")]
    )
    agent = _agent(tmp_path, client, mode="architect")

    async def confirm(name: str, args: dict[str, Any]) -> bool:
        seen.append(name)
        return True

    agent.confirmation_callback = confirm
    await agent.process_user_input("set x to 9")

    assert seen == ["edit_file"]  # ARCHITECT confirms even edits


@pytest.mark.asyncio
async def test_disabling_loop_uses_single_shot(tmp_path: Path) -> None:
    """enable_agent_loop=False restores the legacy single-shot path."""
    client = ScriptedToolClient([])  # chat_with_tools must never be called
    agent = _agent(tmp_path, client, mode="execute")
    agent.settings.set_preference("enable_agent_loop", False)

    out = await agent.process_user_input("hello")
    assert out == "single-shot answer"
