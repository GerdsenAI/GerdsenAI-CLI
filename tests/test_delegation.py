"""Sub-agent delegation: the delegate tool + run_delegation.

A parent turn can spawn a focused child loop. Because the parent and child share
the one scripted client, the script is simply ordered across the nested loops:
the parent's `delegate` call runs the child loop (which consumes the next scripted
results) before the parent continues.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gerdsenai_cli.core.agent_tools import build_default_registry
from gerdsenai_cli.core.delegation import run_delegation
from tests.harness import ScriptedLLMClient, build_agent, final, tool_call


@pytest.mark.asyncio
async def test_delegate_runs_child_loop_that_edits_a_file(tmp_path: Path) -> None:
    """A parent delegate -> child read->edit->final edits a file in one parent turn."""
    target = tmp_path / "hello.py"
    target.write_text("print('old')\n")

    client = ScriptedLLMClient(
        [
            tool_call("delegate", task="make hello.py print new"),
            # --- child loop (consumes these) ---
            tool_call("read_file", path=str(target)),
            tool_call("edit_file", path=str(target), new_content="print('new')\n"),
            final("Edited hello.py."),
            # --- parent resumes ---
            final("Delegated the edit; all done."),
        ]
    )
    agent = build_agent(tmp_path, client, mode="execute")

    out = await agent.process_user_input("delegate the hello.py edit")

    assert "all done" in out
    assert target.read_text() == "print('new')\n"  # the child's edit hit disk


@pytest.mark.asyncio
async def test_depth_cap_omits_delegate_in_child_registry(tmp_path: Path) -> None:
    """The top agent has `delegate`; a child at max depth does not."""
    agent = build_agent(tmp_path, ScriptedLLMClient(), mode="execute")  # max_depth=1
    top = build_default_registry(agent, delegation_depth=0)
    child = build_default_registry(agent, delegation_depth=1)
    assert top.get("delegate") is not None
    assert child.get("delegate") is None


@pytest.mark.asyncio
async def test_run_delegation_refuses_past_the_cap(tmp_path: Path) -> None:
    agent = build_agent(tmp_path, ScriptedLLMClient(), mode="execute")
    out = await run_delegation(agent, "anything", depth=2, max_depth=1)
    assert "depth limit" in out.lower()


@pytest.mark.asyncio
async def test_disabled_delegation_has_no_delegate_tool(tmp_path: Path) -> None:
    agent = build_agent(
        tmp_path,
        ScriptedLLMClient(),
        mode="execute",
        preferences={"enable_delegation": False},
    )
    assert build_default_registry(agent).get("delegate") is None


@pytest.mark.asyncio
async def test_architect_confirms_the_spawn(tmp_path: Path) -> None:
    """ARCHITECT routes the delegate spawn through the confirm gate."""
    seen: list[str] = []

    async def confirm(name: str, args: dict) -> bool:
        seen.append(name)
        return True

    client = ScriptedLLMClient(
        [
            tool_call("delegate", task="just answer the question"),
            final("child answer"),  # child finalizes immediately (no tools)
            final("parent answer"),
        ]
    )
    agent = build_agent(tmp_path, client, mode="architect")
    agent.confirmation_callback = confirm

    await agent.process_user_input("delegate this")
    assert seen == ["delegate"]  # the spawn was confirmed


@pytest.mark.asyncio
async def test_child_run_command_still_confirms_in_execute(tmp_path: Path) -> None:
    """EXECUTE auto-allows the spawn, but the child's run_command still confirms."""
    seen: list[str] = []

    async def confirm(name: str, args: dict) -> bool:
        seen.append(name)
        return False  # deny the shell command

    client = ScriptedLLMClient(
        [
            tool_call("delegate", task="run a shell command"),
            tool_call("run_command", command="echo hi"),  # child
            final("child handled the denial"),
            final("parent done"),
        ]
    )
    agent = build_agent(tmp_path, client, mode="execute")
    agent.confirmation_callback = confirm

    await agent.process_user_input("delegate a shell command")

    assert "run_command" in seen  # the child's shell command hit the gate
    assert "delegate" not in seen  # EXECUTE auto-allowed the spawn itself
