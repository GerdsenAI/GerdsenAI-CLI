"""Tests for MCP-as-tools: the SDK wrapper and the loop-tool builder.

No network or subprocess: the MCP session is mocked, and the SDK-absent / server-
unreachable paths are exercised directly so the graceful-degradation guarantees
are pinned. Tests that need the real ``mcp`` SDK are gated with importorskip.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from gerdsenai_cli.core.mcp_client import MCPClient
from gerdsenai_cli.core.mcp_tools import build_mcp_tools
from gerdsenai_cli.core.tool_registry import Tool, ToolRegistry


def _settings(servers: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(mcp_servers=servers)


# --------------------------------------------------------------------------- #
# build_mcp_tools — graceful degradation
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_no_servers_returns_no_tools() -> None:
    assert await build_mcp_tools(_settings({})) == []


@pytest.mark.asyncio
async def test_missing_settings_attr_returns_no_tools() -> None:
    assert await build_mcp_tools(SimpleNamespace()) == []


@pytest.mark.asyncio
async def test_sdk_absent_returns_no_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MCPClient, "sdk_available", staticmethod(lambda: False))
    settings = _settings({"srv": {"url": "http://localhost:9000/mcp"}})
    assert await build_mcp_tools(settings) == []


@pytest.mark.asyncio
async def test_unreachable_server_contributes_no_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(MCPClient, "sdk_available", staticmethod(lambda: True))

    async def _empty(self: MCPClient) -> list[dict[str, Any]]:
        return []

    monkeypatch.setattr(MCPClient, "list_tools", _empty)
    settings = _settings({"srv": {"url": "http://localhost:9000/mcp"}})
    assert await build_mcp_tools(settings) == []


@pytest.mark.asyncio
async def test_server_without_url_is_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(MCPClient, "sdk_available", staticmethod(lambda: True))
    settings = _settings({"srv": {}})  # no url
    assert await build_mcp_tools(settings) == []


# --------------------------------------------------------------------------- #
# build_mcp_tools — happy path
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_builds_prefixed_mutating_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(MCPClient, "sdk_available", staticmethod(lambda: True))

    async def _schemas(self: MCPClient) -> list[dict[str, Any]]:
        return [
            {
                "name": "search",
                "description": "Search the web",
                "inputSchema": {
                    "type": "object",
                    "properties": {"q": {"type": "string"}},
                },
            },
            {"name": "fetch", "description": "", "inputSchema": None},
        ]

    monkeypatch.setattr(MCPClient, "list_tools", _schemas)
    settings = _settings({"web": {"url": "http://localhost:9000/mcp"}})

    tools = await build_mcp_tools(settings)
    assert [t.name for t in tools] == ["mcp__web__search", "mcp__web__fetch"]
    assert all(isinstance(t, Tool) for t in tools)
    # MCP tools have external side effects -> must be gated by the confirm flow.
    assert all(t.mutating for t in tools)
    # A tool with no inputSchema gets a safe empty-object schema.
    fetch = next(t for t in tools if t.name == "mcp__web__fetch")
    assert fetch.parameters == {"type": "object", "properties": {}}
    # And a tool with no description gets a sensible default.
    assert "fetch" in fetch.description


@pytest.mark.asyncio
async def test_built_tools_register_and_invoke(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(MCPClient, "sdk_available", staticmethod(lambda: True))

    async def _schemas(self: MCPClient) -> list[dict[str, Any]]:
        return [{"name": "echo", "description": "Echo", "inputSchema": {}}]

    calls: list[tuple[str, dict[str, Any]]] = []

    async def _call(self: MCPClient, name: str, arguments: dict[str, Any]) -> str:
        calls.append((name, arguments))
        return f"echoed: {arguments.get('text', '')}"

    monkeypatch.setattr(MCPClient, "list_tools", _schemas)
    monkeypatch.setattr(MCPClient, "call_tool", _call)

    tools = await build_mcp_tools(_settings({"e": {"url": "http://x/mcp"}}))
    registry = ToolRegistry()
    for tool in tools:
        registry.register(tool)

    tool = registry.get("mcp__e__echo")
    assert tool is not None
    result = await tool.run({"text": "hi"})
    assert result == "echoed: hi"
    # The remote (unprefixed) name is what gets sent to the server.
    assert calls == [("echo", {"text": "hi"})]


# --------------------------------------------------------------------------- #
# MCPClient — SDK-absent degradation (no monkeypatch; mcp really is absent here)
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_client_list_tools_empty_when_sdk_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(MCPClient, "sdk_available", staticmethod(lambda: False))
    client = MCPClient("http://localhost:9000/mcp", name="srv")
    assert await client.list_tools() == []


@pytest.mark.asyncio
async def test_client_call_tool_hint_when_sdk_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(MCPClient, "sdk_available", staticmethod(lambda: False))
    client = MCPClient("http://localhost:9000/mcp", name="srv")
    msg = await client.call_tool("anything", {})
    assert "not installed" in msg
    assert "gerdsenai-cli[mcp]" in msg


@pytest.mark.asyncio
async def test_client_aclose_is_safe() -> None:
    client = MCPClient("http://localhost:9000/mcp", name="srv")
    assert await client.aclose() is None


# --------------------------------------------------------------------------- #
# MCPClient._flatten_content
# --------------------------------------------------------------------------- #


def test_flatten_joins_text_blocks() -> None:
    result = SimpleNamespace(
        content=[SimpleNamespace(text="line one"), SimpleNamespace(text="line two")],
        isError=False,
    )
    assert MCPClient._flatten_content(result) == "line one\nline two"


def test_flatten_non_text_block_summarized() -> None:
    result = SimpleNamespace(
        content=[SimpleNamespace(type="image", text=None)], isError=False
    )
    assert MCPClient._flatten_content(result) == "[image block]"


def test_flatten_empty_content() -> None:
    result = SimpleNamespace(content=[], isError=False)
    assert MCPClient._flatten_content(result) == "(no output)"


def test_flatten_marks_error_results() -> None:
    result = SimpleNamespace(content=[SimpleNamespace(text="boom")], isError=True)
    out = MCPClient._flatten_content(result)
    assert "error" in out.lower()
    assert "boom" in out


# --------------------------------------------------------------------------- #
# SDK-gated: only runs where the real mcp SDK is installed
# --------------------------------------------------------------------------- #


def test_sdk_available_reflects_real_import() -> None:
    pytest.importorskip("mcp")
    assert MCPClient.sdk_available() is True


# --------------------------------------------------------------------------- #
# Agent wire-in: _ensure_tool_registry merges MCP tools (and caches)
# --------------------------------------------------------------------------- #


def _agent(tmp_path: Any, servers: dict[str, Any]) -> Any:
    from gerdsenai_cli.config.settings import Settings
    from gerdsenai_cli.core.agent import Agent

    settings = Settings()
    settings.set_preference("enable_llm_intent_detection", False)
    settings.mcp_servers = servers

    class _Client:
        def get_model_context_window(self, model_id: str) -> int:
            return 8192

    return Agent(_Client(), settings, project_root=tmp_path)


@pytest.mark.asyncio
async def test_ensure_registry_without_servers_is_default_only(tmp_path: Any) -> None:
    agent = _agent(tmp_path, {})
    default = agent._get_tool_registry()
    before = len(default)
    registry = await agent._ensure_tool_registry()
    assert registry is default
    assert len(registry) == before  # unchanged: no MCP servers configured


@pytest.mark.asyncio
async def test_ensure_registry_adds_mcp_tools_once(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import gerdsenai_cli.core.mcp_tools as mt

    agent = _agent(tmp_path, {"srv": {"url": "http://x/mcp"}})
    before = len(agent._get_tool_registry())

    async def _fake_build(settings: Any) -> list[Tool]:
        async def _noop(**kwargs: Any) -> str:
            return "ok"

        return [
            Tool(
                name="mcp__srv__do",
                description="d",
                parameters={"type": "object", "properties": {}},
                func=_noop,
                mutating=True,
            )
        ]

    calls = {"n": 0}
    orig = _fake_build

    async def _counting(settings: Any) -> list[Tool]:
        calls["n"] += 1
        return await orig(settings)

    monkeypatch.setattr(mt, "build_mcp_tools", _counting)

    registry = await agent._ensure_tool_registry()
    assert registry.get("mcp__srv__do") is not None
    assert len(registry) == before + 1
    # Cached: a second call does not re-list the servers.
    await agent._ensure_tool_registry()
    assert calls["n"] == 1
