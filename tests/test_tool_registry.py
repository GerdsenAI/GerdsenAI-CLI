"""Phase 2: the tool registry + agentic loop engine.

Drives run_agent_loop with a scripted fake client (no network) to prove the
loop actually chains tool calls within a single turn, honors the confirm gate,
respects CHAT mode, and stops safely on the iteration cap / errors.
"""

from __future__ import annotations

from typing import Any

import pytest

from gerdsenai_cli.core.llm_client import ChatMessage, ChatResult, ToolCall
from gerdsenai_cli.core.tool_registry import (
    Tool,
    ToolRegistry,
    run_agent_loop,
)


class ScriptedClient:
    """A fake LLMClient that returns a pre-scripted sequence of ChatResults.

    Native tool-calling is used (use_native_tools=True in tests), so only
    chat_with_tools is exercised; chat() backs the CHAT-mode path.
    """

    def __init__(self, script: list[ChatResult]) -> None:
        self._script = list(script)
        self.calls = 0
        self.last_convo: list[ChatMessage] | None = None

    async def chat_with_tools(
        self, messages: list[ChatMessage], tools: list[dict[str, Any]], **kw: Any
    ) -> ChatResult:
        self.last_convo = list(messages)
        self.calls += 1
        return self._script.pop(0)

    async def chat(self, messages: list[ChatMessage], **kw: Any) -> str:
        self.last_convo = list(messages)
        self.calls += 1
        return "plain chat answer"


def _registry(record: list[str] | None = None) -> ToolRegistry:
    reg = ToolRegistry()

    async def read_file(path: str) -> str:
        if record is not None:
            record.append(f"read:{path}")
        return f"contents of {path}"

    async def write_file(path: str, content: str) -> str:
        if record is not None:
            record.append(f"write:{path}")
        return f"wrote {path}"

    reg.register(
        Tool(
            name="read_file",
            description="Read a file",
            parameters={"type": "object", "properties": {"path": {"type": "string"}}},
            func=read_file,
        )
    )
    reg.register(
        Tool(
            name="write_file",
            description="Write a file",
            parameters={"type": "object", "properties": {}},
            func=write_file,
            mutating=True,
        )
    )
    return reg


def _call(name: str, **args: Any) -> ChatResult:
    return ChatResult(
        content="", tool_calls=[ToolCall(id=f"c_{name}", name=name, arguments=args)]
    )


def _final(text: str) -> ChatResult:
    return ChatResult(content=text)


# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_multi_step_tool_use_in_one_turn() -> None:
    """The loop chains read -> write -> final within a single call."""
    record: list[str] = []
    client = ScriptedClient(
        [
            _call("read_file", path="a.py"),
            _call("write_file", path="b.py", content="x"),
            _final("done: edited b.py based on a.py"),
        ]
    )
    result = await run_agent_loop(
        client,  # type: ignore[arg-type]
        [ChatMessage(role="user", content="port a.py into b.py")],
        _registry(record),
        use_native_tools=True,
    )
    assert record == ["read:a.py", "write:b.py"]
    assert result.stopped_reason == "final"
    assert result.tool_calls_made == 2
    assert "edited b.py" in result.content


@pytest.mark.asyncio
async def test_chat_mode_runs_no_tools() -> None:
    """allow_tools=False => one plain completion, no tool calls."""
    client = ScriptedClient([])  # chat_with_tools must never be called
    result = await run_agent_loop(
        client,  # type: ignore[arg-type]
        [ChatMessage(role="user", content="hello")],
        _registry(),
        allow_tools=False,
    )
    assert result.content == "plain chat answer"
    assert result.tool_calls_made == 0
    assert result.iterations == 0


@pytest.mark.asyncio
async def test_confirm_denies_mutating_tool() -> None:
    """A denied mutating tool is skipped; the model is told, and it recovers."""
    record: list[str] = []
    client = ScriptedClient(
        [
            _call("write_file", path="b.py", content="x"),
            _final("ok, I won't write the file"),
        ]
    )

    async def deny(name: str, args: dict[str, Any]) -> bool:
        return False

    result = await run_agent_loop(
        client,  # type: ignore[arg-type]
        [ChatMessage(role="user", content="write b.py")],
        _registry(record),
        confirm=deny,
        use_native_tools=True,
    )
    assert record == []  # the write never executed
    assert result.stopped_reason == "final"
    # The tool-result message told the model it was declined.
    assert client.last_convo is not None
    assert any(m.role == "tool" and "declined" in m.content for m in client.last_convo)


@pytest.mark.asyncio
async def test_confirm_allows_then_runs() -> None:
    record: list[str] = []
    client = ScriptedClient(
        [_call("write_file", path="b.py", content="x"), _final("written")]
    )

    async def allow(name: str, args: dict[str, Any]) -> bool:
        return True

    await run_agent_loop(
        client,  # type: ignore[arg-type]
        [ChatMessage(role="user", content="write b.py")],
        _registry(record),
        confirm=allow,
        use_native_tools=True,
    )
    assert record == ["write:b.py"]


@pytest.mark.asyncio
async def test_read_only_tool_bypasses_confirm() -> None:
    """A read-only tool runs even when confirm would deny."""
    record: list[str] = []
    client = ScriptedClient([_call("read_file", path="a.py"), _final("read it")])

    async def deny(name: str, args: dict[str, Any]) -> bool:
        return False

    await run_agent_loop(
        client,  # type: ignore[arg-type]
        [ChatMessage(role="user", content="read a.py")],
        _registry(record),
        confirm=deny,
        use_native_tools=True,
    )
    assert record == ["read:a.py"]  # ran despite deny (not mutating)


@pytest.mark.asyncio
async def test_unknown_tool_is_reported_not_fatal() -> None:
    client = ScriptedClient([_call("nonexistent"), _final("recovered")])
    result = await run_agent_loop(
        client,  # type: ignore[arg-type]
        [ChatMessage(role="user", content="do a thing")],
        _registry(),
        use_native_tools=True,
    )
    assert result.stopped_reason == "final"
    assert client.last_convo is not None
    assert any(
        m.role == "tool" and "unknown tool" in m.content for m in client.last_convo
    )


@pytest.mark.asyncio
async def test_tool_exception_does_not_kill_loop() -> None:
    reg = ToolRegistry()

    async def boom() -> str:
        raise RuntimeError("kaboom")

    reg.register(
        Tool(
            name="boom",
            description="explodes",
            parameters={"type": "object", "properties": {}},
            func=boom,
        )
    )
    client = ScriptedClient([_call("boom"), _final("handled the error")])
    result = await run_agent_loop(
        client,  # type: ignore[arg-type]
        [ChatMessage(role="user", content="go")],
        reg,
        use_native_tools=True,
    )
    assert result.stopped_reason == "final"
    assert client.last_convo is not None
    assert any(m.role == "tool" and "kaboom" in m.content for m in client.last_convo)


@pytest.mark.asyncio
async def test_max_iterations_cap() -> None:
    """A model that loops forever is stopped at the cap."""
    # Always asks to read again, never finalizes.
    forever = [_call("read_file", path="a.py") for _ in range(50)]
    client = ScriptedClient(forever)
    result = await run_agent_loop(
        client,  # type: ignore[arg-type]
        [ChatMessage(role="user", content="loop")],
        _registry(),
        use_native_tools=True,
        max_iterations=3,
    )
    assert result.stopped_reason == "max_iterations"
    assert result.iterations == 3
    assert client.calls == 3


@pytest.mark.asyncio
async def test_empty_registry_falls_back_to_plain_chat() -> None:
    client = ScriptedClient([])
    result = await run_agent_loop(
        client,  # type: ignore[arg-type]
        [ChatMessage(role="user", content="hi")],
        ToolRegistry(),  # no tools
    )
    assert result.content == "plain chat answer"
    assert result.tool_calls_made == 0


# --------------------------------------------------------------------------- #
# registry/tool unit bits
# --------------------------------------------------------------------------- #


def test_tool_to_schema_is_openai_shape() -> None:
    t = Tool(
        name="f",
        description="d",
        parameters={"type": "object", "properties": {"x": {"type": "string"}}},
        func=_noop_tool,
    )
    schema = t.to_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "f"
    assert schema["function"]["parameters"]["properties"] == {"x": {"type": "string"}}


def test_registry_schemas_and_len() -> None:
    reg = _registry()
    assert len(reg) == 2
    names = {s["function"]["name"] for s in reg.schemas()}
    assert names == {"read_file", "write_file"}


async def _noop_tool() -> str:
    return ""
