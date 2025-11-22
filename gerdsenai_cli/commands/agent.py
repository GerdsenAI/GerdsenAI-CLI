"""
Agent management commands for GerdsenAI CLI.

This module implements commands for managing the AI agent, including conversation
management, agent statistics, and agent configuration.
"""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..config.manager import ConfigManager
from ..utils.helpers import format_duration, format_size
from .base import BaseCommand, CommandArgument, CommandCategory, CommandResult

if TYPE_CHECKING:
    from ..core.agent import Agent


class AgentStatusCommand(BaseCommand):
    """Display current agent status and statistics."""

    name = "agent"
    description = "Display current agent status and statistics"
    category = CommandCategory.AGENT
    aliases = ["agent-status", "status-agent"]

    arguments = [
        CommandArgument(
            name="--detailed",
            description="Show detailed agent information",
            required=False,
            arg_type=bool,
            default=False,
        )
    ]

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        """Execute the agent status command."""
        console = Console()

        try:
            # Get agent from context
            agent = getattr(context, "agent", None) if context else None
            if not agent:
                console.print("[yellow]Agent not initialized.[/yellow]")
                return CommandResult(success=True, message="Agent not initialized")

            # Display agent status
            if args.get("detailed", False):
                await self._display_detailed_status(console, agent, context)
            else:
                await self._display_simple_status(console, agent, context)

            return CommandResult(
                success=True,
                message="Displayed agent status",
                data={"agent_active": True},
            )

        except Exception as e:
            error_msg = f"Failed to get agent status: {str(e)}"
            console.print(f"[red]Error: {error_msg}[/red]")
            return CommandResult(success=False, message=error_msg)

    async def _display_simple_status(
        self, console: Console, agent: "Agent", context: Any
    ):
        """Display simple agent status."""
        stats = agent.get_stats()

        # Create status table
        table = Table(title="Agent Status", show_header=True, header_style="bold green")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")

        table.add_row("Status", "🟢 Active")
        table.add_row("Total Conversations", str(stats.get("total_conversations", 0)))
        table.add_row("Total Messages", str(stats.get("total_messages", 0)))
        table.add_row("Files Processed", str(stats.get("files_processed", 0)))
        table.add_row("Actions Executed", str(stats.get("actions_executed", 0)))

        if stats.get("last_activity"):
            table.add_row("Last Activity", stats["last_activity"])

        console.print(table)

    async def _display_detailed_status(
        self, console: Console, agent: "Agent", context: Any
    ):
        """Display detailed agent status."""
        stats = agent.get_stats()

        # Agent Overview Panel
        overview_lines = [
            "[bold]Status:[/bold] 🟢 Active and Ready",
            f"[bold]Session Duration:[/bold] {format_duration(stats.get('session_duration', 0))}",
            f"[bold]Memory Usage:[/bold] {format_size(stats.get('memory_usage', 0))}",
        ]

        if stats.get("current_model"):
            overview_lines.append(
                f"[bold]Current Model:[/bold] {stats['current_model']}"
            )

        overview_panel = Panel(
            "\n".join(overview_lines), title="Agent Overview", border_style="green"
        )
        console.print(overview_panel)
        console.print()

        # Activity Statistics
        activity_table = Table(
            title="Activity Statistics", show_header=True, header_style="bold blue"
        )
        activity_table.add_column("Activity Type", style="cyan")
        activity_table.add_column("Count", justify="right")
        activity_table.add_column("Last Occurrence", style="dim")

        activities = [
            (
                "Conversations",
                stats.get("total_conversations", 0),
                stats.get("last_conversation"),
            ),
            (
                "Messages Processed",
                stats.get("total_messages", 0),
                stats.get("last_message"),
            ),
            ("Files Read", stats.get("files_read", 0), stats.get("last_file_read")),
            ("Files Edited", stats.get("files_edited", 0), stats.get("last_file_edit")),
            (
                "Files Created",
                stats.get("files_created", 0),
                stats.get("last_file_create"),
            ),
            (
                "Search Operations",
                stats.get("searches_performed", 0),
                stats.get("last_search"),
            ),
            (
                "Code Analysis",
                stats.get("code_analyses", 0),
                stats.get("last_analysis"),
            ),
        ]

        for activity_type, count, last_time in activities:
            activity_table.add_row(activity_type, str(count), last_time or "Never")

        console.print(activity_table)
        console.print()

        # Context Information
        if hasattr(context, "context_manager"):
            context_stats = context.context_manager.get_stats()
            context_lines = [
                f"[bold]Project Files:[/bold] {context_stats.get('total_files', 0)}",
                f"[bold]Cached Files:[/bold] {context_stats.get('cached_files', 0)}",
                f"[bold]Cache Hit Rate:[/bold] {context_stats.get('cache_hit_rate', 0):.1%}",
                f"[bold]Context Size:[/bold] {format_size(context_stats.get('context_size', 0))}",
            ]

            context_panel = Panel(
                "\n".join(context_lines), title="Context Manager", border_style="blue"
            )
            console.print(context_panel)


class ChatCommand(BaseCommand):
    """Manage conversation history and context."""

    name = "chat"
    description = "Manage conversation history and context"
    category = CommandCategory.AGENT
    aliases = ["conversation", "conv", "chat-history"]

    arguments = [
        CommandArgument(
            name="action",
            description="Action to perform: show, clear, save, load",
            required=True,
            arg_type=str,
        ),
        CommandArgument(
            name="--limit",
            description="Limit number of messages to show",
            required=False,
            arg_type=int,
            default=10,
        ),
        CommandArgument(
            name="--file",
            description="File path for save/load operations",
            required=False,
            arg_type=str,
            default=None,
        ),
    ]

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        """Execute the conversation command."""
        console = Console()
        action = args.get("action", "").lower()

        try:
            agent = getattr(context, "agent", None) if context else None
            if not agent:
                console.print("[red]Agent not initialized.[/red]")
                return CommandResult(success=False, message="Agent not initialized")

            if action == "show":
                return await self._show_conversation(console, agent, args)
            elif action == "clear":
                return await self._clear_conversation(console, agent, args)
            elif action == "save":
                return await self._save_conversation(console, agent, args)
            elif action == "load":
                return await self._load_conversation(console, agent, args)
            else:
                console.print(f"[red]Unknown action: {action}[/red]")
                console.print("[dim]Available actions: show, clear, save, load[/dim]")
                return CommandResult(success=False, message=f"Unknown action: {action}")

        except Exception as e:
            error_msg = f"Failed to manage conversation: {str(e)}"
            console.print(f"[red]Error: {error_msg}[/red]")
            return CommandResult(success=False, message=error_msg)

    async def _show_conversation(
        self, console: Console, agent: "Agent", args: dict[str, Any]
    ) -> CommandResult:
        """Show conversation history."""
        limit = args.get("limit", 10)
        history = agent.get_conversation_history(limit=limit)

        if not history:
            console.print("[yellow]No conversation history available.[/yellow]")
            return CommandResult(success=True, message="No conversation history")

        table = Table(
            title=f"Recent Conversation (Last {len(history)} messages)",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Time", style="dim", width=20)
        table.add_column("Role", style="cyan", width=8)
        table.add_column("Message", style="white")

        for entry in history:
            timestamp = entry.get("timestamp", "Unknown")
            role = entry.get("role", "unknown").title()
            message = entry.get("content", "")

            # Truncate long messages
            if len(message) > 100:
                message = message[:97] + "..."

            table.add_row(timestamp, role, message)

        console.print(table)
        return CommandResult(success=True, message=f"Showed {len(history)} messages")

    async def _clear_conversation(
        self, console: Console, agent: "Agent", args: dict[str, Any]
    ) -> CommandResult:
        """Clear conversation history."""
        agent.clear_conversation()
        console.print("[green]✓[/green] Conversation history cleared.")
        return CommandResult(success=True, message="Conversation cleared")

    async def _save_conversation(
        self, console: Console, agent: "Agent", args: dict[str, Any]
    ) -> CommandResult:
        """Save conversation to file."""
        file_path = args.get("file")
        if not file_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"conversation_{timestamp}.json"

        history = agent.get_conversation_history()

        try:
            with open(file_path, "w") as f:
                json.dump(history, f, indent=2, default=str)

            console.print(f"[green]✓[/green] Conversation saved to: {file_path}")
            return CommandResult(success=True, message=f"Saved to {file_path}")

        except Exception as e:
            console.print(f"[red]Failed to save conversation: {e}[/red]")
            return CommandResult(success=False, message=f"Save failed: {e}")

    async def _load_conversation(
        self, console: Console, agent: "Agent", args: dict[str, Any]
    ) -> CommandResult:
        """Load conversation from file."""
        file_path = args.get("file")
        if not file_path:
            console.print("[red]File path required for load operation.[/red]")
            return CommandResult(success=False, message="File path required")

        try:
            with open(file_path) as f:
                history = json.load(f)

            agent.load_conversation_history(history)
            console.print(f"[green]✓[/green] Conversation loaded from: {file_path}")
            return CommandResult(success=True, message=f"Loaded from {file_path}")

        except FileNotFoundError:
            console.print(f"[red]File not found: {file_path}[/red]")
            return CommandResult(success=False, message="File not found")
        except Exception as e:
            console.print(f"[red]Failed to load conversation: {e}[/red]")
            return CommandResult(success=False, message=f"Load failed: {e}")


class RefreshContextCommand(BaseCommand):
    """Refresh the project context and file cache."""

    name = "refresh"
    description = "Refresh the project context and file cache"
    category = CommandCategory.AGENT
    aliases = ["refresh-context", "reload-context"]

    arguments = [
        CommandArgument(
            name="--deep",
            description="Perform deep refresh (re-read all files)",
            required=False,
            arg_type=bool,
            default=False,
        )
    ]

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        """Execute the refresh context command."""
        console = Console()

        try:
            context_manager = (
                getattr(context, "context_manager", None) if context else None
            )
            if not context_manager:
                console.print("[red]Context manager not available.[/red]")
                return CommandResult(
                    success=False, message="Context manager not available"
                )

            deep_refresh = args.get("deep", False)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Refreshing project context...", total=None)

                if deep_refresh:
                    # Clear cache and re-scan everything
                    context_manager.clear_cache()
                    await context_manager.scan_directory()
                else:
                    # Just refresh file list and update cache
                    await context_manager.refresh()

                progress.update(task, description="Context refresh complete!")

            stats = context_manager.get_stats()
            console.print("[green]✓[/green] Context refreshed successfully!")
            console.print(
                f"[dim]Files: {stats.get('total_files', 0)}, "
                f"Cached: {stats.get('cached_files', 0)}, "
                f"Size: {format_size(stats.get('context_size', 0))}[/dim]"
            )

            return CommandResult(
                success=True,
                message="Context refreshed",
                data={"stats": stats, "deep_refresh": deep_refresh},
            )

        except Exception as e:
            error_msg = f"Failed to refresh context: {str(e)}"
            console.print(f"[red]Error: {error_msg}[/red]")
            return CommandResult(success=False, message=error_msg)


class ResetCommand(BaseCommand):
    """Clear the current session and reset agent state."""

    name = "reset"
    description = "Clear the current session and reset agent state"
    category = CommandCategory.AGENT
    aliases = ["clear", "clear-session"]

    arguments = [
        CommandArgument(
            name="--keep-context",
            description="Keep project context when clearing",
            required=False,
            arg_type=bool,
            default=False,
        )
    ]

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        """Execute the clear session command."""
        console = Console()

        try:
            agent = getattr(context, "agent", None) if context else None
            if not agent:
                console.print("[yellow]No active agent session to clear.[/yellow]")
                return CommandResult(success=True, message="No active session")

            keep_context = args.get("keep_context", False)

            # Clear agent state
            agent.clear_conversation()

            # Optionally clear context
            if not keep_context and hasattr(context, "context_manager"):
                context.context_manager.clear_cache()

            console.print("[green]✓[/green] Session cleared successfully!")
            if keep_context:
                console.print("[dim]Project context retained.[/dim]")
            else:
                console.print("[dim]Project context also cleared.[/dim]")

            return CommandResult(
                success=True,
                message="Session cleared",
                data={"keep_context": keep_context},
            )

        except Exception as e:
            error_msg = f"Failed to clear session: {str(e)}"
            console.print(f"[red]Error: {error_msg}[/red]")
            return CommandResult(success=False, message=error_msg)


class AgentConfigCommand(BaseCommand):
    """Configure agent behavior and settings."""

    name = "agent-config"
    description = "Configure agent behavior and settings"
    category = CommandCategory.AGENT
    aliases = ["configure-agent", "agent-settings"]

    arguments = [
        CommandArgument(
            name="setting",
            description="Setting to view or modify",
            required=False,
            arg_type=str,
            default=None,
        ),
        CommandArgument(
            name="value",
            description="New value for the setting",
            required=False,
            arg_type=str,
            default=None,
        ),
        CommandArgument(
            name="--list",
            description="List all available settings",
            required=False,
            arg_type=bool,
            default=False,
        ),
    ]

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        """Execute the agent config command."""
        console = Console()

        try:
            config = ConfigManager()

            if args.get("list", False):
                return await self._list_settings(console, config)

            setting = args.get("setting")
            value = args.get("value")

            if not setting:
                return await self._show_all_settings(console, config)

            if value is None:
                return await self._show_setting(console, config, setting)
            else:
                return await self._update_setting(console, config, setting, value)

        except Exception as e:
            error_msg = f"Failed to manage agent config: {str(e)}"
            console.print(f"[red]Error: {error_msg}[/red]")
            return CommandResult(success=False, message=error_msg)

    async def _list_settings(
        self, console: Console, config: ConfigManager
    ) -> CommandResult:
        """List all available agent settings."""
        settings_info = {
            "max_context_length": "Maximum context length for conversations",
            "auto_save_conversations": "Automatically save conversations",
            "confirm_file_edits": "Require confirmation before editing files",
            "verbose_logging": "Enable verbose logging",
            "cache_responses": "Cache LLM responses for efficiency",
            "max_file_size": "Maximum file size to process (bytes)",
            "default_temperature": "Default temperature for LLM requests",
            "response_timeout": "Timeout for LLM responses (seconds)",
        }

        table = Table(
            title="Available Agent Settings", show_header=True, header_style="bold blue"
        )
        table.add_column("Setting", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Current Value", justify="right", style="green")

        for setting, description in settings_info.items():
            current_value = config.get_setting(f"agent.{setting}", "Not set")
            table.add_row(setting, description, str(current_value))

        console.print(table)
        return CommandResult(success=True, message="Listed available settings")

    async def _show_all_settings(
        self, console: Console, config: ConfigManager
    ) -> CommandResult:
        """Show all current agent settings."""
        agent_settings = config.get_setting("agent", {})

        if not agent_settings:
            console.print("[yellow]No agent settings configured.[/yellow]")
            return CommandResult(success=True, message="No settings configured")

        table = Table(
            title="Current Agent Settings", show_header=True, header_style="bold green"
        )
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")

        for key, value in agent_settings.items():
            table.add_row(key, str(value))

        console.print(table)
        return CommandResult(success=True, message="Displayed all settings")

    async def _show_setting(
        self, console: Console, config: ConfigManager, setting: str
    ) -> CommandResult:
        """Show a specific agent setting."""
        value = config.get_setting(f"agent.{setting}", None)

        if value is None:
            console.print(f"[yellow]Setting '{setting}' is not configured.[/yellow]")
        else:
            console.print(f"[cyan]{setting}[/cyan]: [white]{value}[/white]")

        return CommandResult(success=True, message=f"Displayed setting: {setting}")

    async def _update_setting(
        self, console: Console, config: ConfigManager, setting: str, value: str
    ) -> CommandResult:
        """Update a specific agent setting."""
        # Convert string value to appropriate type
        converted_value = self._convert_value(value)

        old_value = config.get_setting(f"agent.{setting}", None)
        config.update_setting(f"agent.{setting}", converted_value)

        console.print(
            f"[green]✓[/green] Updated [cyan]{setting}[/cyan]: [dim]{old_value}[/dim] → [white]{converted_value}[/white]"
        )

        return CommandResult(
            success=True,
            message=f"Updated setting: {setting}",
            data={
                "setting": setting,
                "old_value": old_value,
                "new_value": converted_value,
            },
        )

    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate Python type."""
        # Try boolean
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Try integer
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        # Return as string
        return value
