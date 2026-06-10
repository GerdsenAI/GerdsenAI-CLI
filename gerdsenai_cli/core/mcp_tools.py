"""Expose configured MCP servers as agent-loop tools.

``build_mcp_tools(settings)`` reads ``settings.mcp_servers`` and, for each
reachable server, lists its tools and wraps each as a :class:`~.tool_registry.Tool`
the agent loop can call. Tool names are prefixed ``mcp__<server>__<tool>`` to
avoid collisions with the built-in tools (and with other servers).

MCP tools are marked ``mutating=True`` so they route through the loop's confirm
gate — an MCP server can have arbitrary side effects, so consent stays sacred.

Everything degrades gracefully: if the ``mcp`` SDK is absent, a server is
unreachable, or it exposes no tools, that server simply contributes no tools and
nothing raises.
"""

from __future__ import annotations

import logging
from typing import Any

from .mcp_client import MCPClient
from .tool_registry import Tool

logger = logging.getLogger(__name__)


def _make_tool(client: MCPClient, server: str, schema: dict[str, Any]) -> Tool:
    """Wrap a single MCP tool schema as a loop Tool bound to its client."""
    remote_name = schema["name"]
    qualified = f"mcp__{server}__{remote_name}"

    async def _run(**arguments: Any) -> str:
        return await client.call_tool(remote_name, arguments)

    description = schema.get("description") or f"MCP tool '{remote_name}' on {server}"
    parameters = schema.get("inputSchema") or {"type": "object", "properties": {}}

    return Tool(
        name=qualified,
        description=description,
        parameters=parameters,
        func=_run,
        mutating=True,  # external side effects -> always gated by confirm
    )


async def build_mcp_tools(settings: Any) -> list[Tool]:
    """Build loop Tools for every tool offered by the configured MCP servers.

    Args:
        settings: Settings object exposing ``mcp_servers`` (``{name: {"url": ...}}``).

    Returns:
        A list of Tools (possibly empty). Never raises; unreachable servers and a
        missing SDK are logged at debug and contribute nothing.
    """
    servers = getattr(settings, "mcp_servers", None) or {}
    if not servers:
        return []

    if not MCPClient.sdk_available():
        logger.debug(
            "MCP servers configured but the 'mcp' SDK is not installed; "
            'install it with: pip install "gerdsenai-cli[mcp]"'
        )
        return []

    tools: list[Tool] = []
    for name, config in servers.items():
        url = (config or {}).get("url")
        if not url:
            continue
        client = MCPClient(url, name=name)
        schemas = await client.list_tools()
        for schema in schemas:
            if not schema.get("name"):
                continue
            tools.append(_make_tool(client, name, schema))
        if schemas:
            logger.debug("MCP '%s': registered %d tool(s).", name, len(schemas))
    return tools
