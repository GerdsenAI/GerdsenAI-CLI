"""Thin async client for Model Context Protocol (MCP) servers.

Wraps the official ``mcp`` Python SDK (an *optional* extra:
``pip install "gerdsenai-cli[mcp]"``) so a local model gains the MCP tool
ecosystem. The SDK is imported lazily and every method degrades gracefully:
if the SDK is missing or the server is unreachable, ``list_tools`` returns ``[]``
and ``call_tool`` returns an error string — nothing raises into the agent loop.

Transport is streamable-HTTP against the configured server URL. The SDK's session
lifecycle is driven by async context managers, so each operation opens a fresh
session (connect → initialize → act → close). This is simple and robust; a pooled
long-lived session can come later if profiling warrants it.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

logger = logging.getLogger(__name__)


class MCPClient:
    """Minimal async wrapper over the MCP streamable-HTTP client.

    Args:
        url: The MCP server's streamable-HTTP endpoint.
        name: A short label for logs (the configured server name).
    """

    def __init__(self, url: str, name: str = "mcp") -> None:
        self.url = url
        self.name = name

    @staticmethod
    def sdk_available() -> bool:
        """True when the optional ``mcp`` SDK can be imported."""
        try:
            import mcp  # noqa: F401
            import mcp.client.streamable_http  # noqa: F401
        except Exception:
            return False
        return True

    @asynccontextmanager
    async def _session(self) -> Any:
        """Yield an initialized MCP ClientSession, or raise on failure.

        Callers are expected to wrap usage in try/except — the public methods do
        so and translate failures into safe defaults.
        """
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async with streamablehttp_client(self.url) as (read, write, _get_id):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session

    async def list_tools(self) -> list[dict[str, Any]]:
        """Return the server's tools as ``{name, description, inputSchema}`` dicts.

        Degrades to ``[]`` when the SDK is absent or the server is unreachable.
        """
        if not self.sdk_available():
            logger.debug("MCP SDK not installed; '%s' offers no tools.", self.name)
            return []
        try:
            async with self._session() as session:
                result = await session.list_tools()
                tools = getattr(result, "tools", []) or []
                return [
                    {
                        "name": t.name,
                        "description": getattr(t, "description", "") or "",
                        "inputSchema": getattr(t, "inputSchema", None)
                        or {"type": "object", "properties": {}},
                    }
                    for t in tools
                ]
        except Exception as e:
            logger.debug("MCP '%s' list_tools failed: %s", self.name, e)
            return []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Call a tool and flatten its content blocks to text.

        Returns an error string (never raises) so a failing MCP call surfaces to
        the model as an observation rather than killing the loop.
        """
        if not self.sdk_available():
            return (
                "MCP support is not installed. "
                'Install it with: pip install "gerdsenai-cli[mcp]"'
            )
        try:
            async with self._session() as session:
                result = await session.call_tool(name, arguments=arguments)
                return self._flatten_content(result)
        except Exception as e:
            logger.debug("MCP '%s' call_tool(%s) failed: %s", self.name, name, e)
            return f"Error calling MCP tool '{name}': {e}"

    @staticmethod
    def _flatten_content(result: Any) -> str:
        """Turn an MCP CallToolResult's content blocks into a single string."""
        blocks = getattr(result, "content", None) or []
        parts: list[str] = []
        for block in blocks:
            # Text blocks expose `.text`; other block types are summarized by type.
            text = getattr(block, "text", None)
            if text is not None:
                parts.append(str(text))
            else:
                parts.append(f"[{getattr(block, 'type', 'content')} block]")
        joined = "\n".join(p for p in parts if p)
        if getattr(result, "isError", False):
            return f"(tool reported an error)\n{joined}" if joined else "(tool error)"
        return joined or "(no output)"

    async def aclose(self) -> None:
        """No persistent resources are held (per-call sessions); present for parity."""
        return None
