"""
MCP (Model Context Protocol) server management commands.

Provides commands for configuring and managing MCP server connections.
"""

import logging
from typing import Any

from rich.console import Console
from rich.table import Table

from .base import BaseCommand, CommandArgument, CommandCategory, CommandResult

console = Console()
logger = logging.getLogger(__name__)


class MCPCommand(BaseCommand):
    """Manage MCP (Model Context Protocol) server connections."""

    @property
    def name(self) -> str:
        return "mcp"

    @property
    def description(self) -> str:
        return "Manage MCP server connections (list, add, remove, connect, status)"

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.SYSTEM

    @property
    def aliases(self) -> list[str]:
        return []

    def _define_arguments(self) -> dict[str, CommandArgument]:
        return {
            "action": CommandArgument(
                name="action",
                description="Action to perform",
                required=False,
                choices=["list", "add", "remove", "connect", "status"],
                default="list",
            ),
            "name": CommandArgument(
                name="name",
                description="MCP server name",
                required=False,
            ),
            "url": CommandArgument(
                name="url",
                description="MCP server URL",
                required=False,
            ),
        }

    async def execute(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
        """Execute MCP command."""
        action = args.get("action", "list")
        settings = context.get("settings")
        config_manager = context.get("config_manager")

        if not settings:
            return CommandResult(
                success=False,
                message="Settings not available",
            )

        # Initialize mcp_servers in settings if not present
        if not hasattr(settings, "mcp_servers"):
            settings.mcp_servers = {}

        if action == "list":
            return await self._list_servers(settings)

        elif action == "add":
            name = args.get("name")
            url = args.get("url")

            if not name or not url:
                return CommandResult(
                    success=False,
                    message="Both name and URL are required for 'add' action.\n\nUsage: /mcp add <name> <url>",
                )

            return await self._add_server(settings, config_manager, name, url)

        elif action == "remove":
            name = args.get("name")

            if not name:
                return CommandResult(
                    success=False,
                    message="Server name is required for 'remove' action.\n\nUsage: /mcp remove <name>",
                )

            return await self._remove_server(settings, config_manager, name)

        elif action == "connect":
            name = args.get("name")

            if not name:
                return CommandResult(
                    success=False,
                    message="Server name is required for 'connect' action.\n\nUsage: /mcp connect <name>",
                )

            return await self._connect_server(settings, name)

        elif action == "status":
            return await self._show_status(settings)

        else:
            return CommandResult(
                success=False,
                message=f"Unknown action: {action}",
            )

    async def _list_servers(self, settings) -> CommandResult:
        """List all configured MCP servers."""
        if not hasattr(settings, "mcp_servers") or not settings.mcp_servers:
            return CommandResult(
                success=True,
                message="No MCP servers configured.\n\nUse '/mcp add <name> <url>' to add a server.",
            )

        table = Table(title="MCP Servers", show_header=True)
        table.add_column("Name", style="cyan")
        table.add_column("URL", style="white")
        table.add_column("Status", style="green")

        for name, config in settings.mcp_servers.items():
            url = config.get("url", "N/A")
            status = config.get("status", "Not connected")
            table.add_row(name, url, status)

        console.print("\n")
        console.print(table)
        console.print("\n")

        return CommandResult(
            success=True,
            message=None,  # Already printed the table
        )

    async def _add_server(self, settings, config_manager, name: str, url: str) -> CommandResult:
        """Add a new MCP server."""
        if not hasattr(settings, "mcp_servers"):
            settings.mcp_servers = {}

        if name in settings.mcp_servers:
            return CommandResult(
                success=False,
                message=f"MCP server '{name}' already exists.\n\nUse '/mcp remove {name}' to remove it first.",
            )

        # Add server configuration
        settings.mcp_servers[name] = {
            "url": url,
            "status": "Not connected",
        }

        # Save settings
        if config_manager:
            await config_manager.save_settings(settings)

        return CommandResult(
            success=True,
            message=f"Added MCP server '{name}' with URL: {url}\n\nUse '/mcp connect {name}' to establish a connection.",
        )

    async def _remove_server(self, settings, config_manager, name: str) -> CommandResult:
        """Remove an MCP server."""
        if not hasattr(settings, "mcp_servers") or name not in settings.mcp_servers:
            return CommandResult(
                success=False,
                message=f"MCP server '{name}' not found.\n\nUse '/mcp list' to see configured servers.",
            )

        # Remove server
        del settings.mcp_servers[name]

        # Save settings
        if config_manager:
            await config_manager.save_settings(settings)

        return CommandResult(
            success=True,
            message=f"Removed MCP server '{name}'",
        )

    async def _connect_server(self, settings, name: str) -> CommandResult:
        """Connect to an MCP server."""
        if not hasattr(settings, "mcp_servers") or name not in settings.mcp_servers:
            return CommandResult(
                success=False,
                message=f"MCP server '{name}' not found.\n\nUse '/mcp list' to see configured servers.",
            )

        # TODO: Implement actual MCP connection logic
        # For now, just update status
        settings.mcp_servers[name]["status"] = "Connected (simulated)"

        return CommandResult(
            success=True,
            message=f"Connected to MCP server '{name}'\n\nNote: Full MCP integration is in development.",
        )

    async def _show_status(self, settings) -> CommandResult:
        """Show MCP connection status."""
        if not hasattr(settings, "mcp_servers") or not settings.mcp_servers:
            return CommandResult(
                success=True,
                message="No MCP servers configured.",
            )

        connected_count = sum(
            1 for config in settings.mcp_servers.values()
            if config.get("status", "").startswith("Connected")
        )
        total_count = len(settings.mcp_servers)

        return CommandResult(
            success=True,
            message=f"MCP Status: {connected_count}/{total_count} servers connected\n\nUse '/mcp list' for details.",
        )
