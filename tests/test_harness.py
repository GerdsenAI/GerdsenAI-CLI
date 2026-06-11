"""Self-tests for the shared verification harness (tests/harness.py).

The harness is the foundation later feature PRs build their end-to-end checks on,
so it gets its own coverage: the scripted client's telemetry, and the
``run_turn`` / ``run_turn_stream`` drivers that report which tools ran and how
many files changed in one user turn.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.harness import (
    ScriptedLLMClient,
    build_agent,
    final,
    run_turn,
    run_turn_stream,
    tool_call,
)


def test_scripted_client_advertises_native_tools() -> None:
    client = ScriptedLLMClient()
    assert client.get_capabilities().supports_tools is True


@pytest.mark.asyncio
async def test_scripted_client_raises_on_exhausted_script() -> None:
    client = ScriptedLLMClient([])  # no tool turns scripted
    with pytest.raises(AssertionError, match="exhausted script"):
        await client.chat_with_tools([], tools=[])


@pytest.mark.asyncio
async def test_run_turn_reports_tools_and_file_changes(tmp_path: Path) -> None:
    """A read -> edit -> final turn reports both tools and the file delta."""
    target = tmp_path / "hello.py"
    target.write_text("print('old')\n")
    client = ScriptedLLMClient(
        [
            tool_call("read_file", path=str(target)),
            tool_call("edit_file", path=str(target), new_content="print('new')\n"),
            final("Done."),
        ]
    )
    agent = build_agent(tmp_path, client, mode="execute")

    result = await run_turn(agent, "make hello.py print new")

    assert result.tools_run == ["read_file", "edit_file"]
    assert result.files_modified == 1
    assert "Done." in result.text
    assert target.read_text() == "print('new')\n"


@pytest.mark.asyncio
async def test_run_turn_stream_assembles_final_text(tmp_path: Path) -> None:
    target = tmp_path / "a.py"
    target.write_text("x = 1\n")
    client = ScriptedLLMClient(
        [tool_call("read_file", path=str(target)), final("a.py sets x to 1.")]
    )
    agent = build_agent(tmp_path, client, mode="execute")

    result = await run_turn_stream(agent, "what does a.py do")

    assert result.tools_run == ["read_file"]
    assert result.files_modified == 0
    assert "a.py sets x to 1." in result.text


@pytest.mark.asyncio
async def test_chat_mode_runs_no_tools(tmp_path: Path) -> None:
    """CHAT mode keeps the single-shot path: no tools, the canned reply."""
    client = ScriptedLLMClient([], chat_reply="hi there")
    agent = build_agent(tmp_path, client, mode="chat")

    result = await run_turn(agent, "just chatting")

    assert result.tools_run == []
    assert result.text == "hi there"
    assert client.chat_calls == 1
