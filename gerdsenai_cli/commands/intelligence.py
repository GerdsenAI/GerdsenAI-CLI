"""
Intelligence status command for GerdsenAI CLI.

Shows detailed intelligence activity history, statistics, and current state.
"""

from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .base import BaseCommand

if TYPE_CHECKING:
    from ..core.agent import Agent
    from ..ui.console import EnhancedConsole

console = Console()


class IntelligenceCommand(BaseCommand):
    """Command to display intelligence activity and statistics."""

    @property
    def name(self) -> str:
        """Get command name."""
        return "intelligence"

    @property
    def description(self) -> str:
        """Get command description."""
        return "Show intelligence activity history and statistics"

    @property
    def usage(self) -> str:
        """Get usage information."""
        return "/intelligence [status|history|stats|clear]"

    @property
    def category(self) -> str:
        """Get command category."""
        return "agent"

    def __init__(
        self, agent: "Agent", enhanced_console: "EnhancedConsole | None" = None
    ):
        """Initialize intelligence command.

        Args:
            agent: The AI agent instance
            enhanced_console: Enhanced console for status display
        """
        self.agent: Agent = agent
        self.enhanced_console: Any = enhanced_console

    async def execute(self, args: list[str]) -> str:
        """Execute the intelligence command.

        Args:
            args: Command arguments

        Returns:
            Result message
        """
        if not self.enhanced_console:
            return "❌ Intelligence tracking not available (enhanced console required)"

        # Default to 'status' if no subcommand
        subcommand = args[0] if args else "status"

        if subcommand == "status":
            return await self._show_status()
        elif subcommand == "history":
            return await self._show_history()
        elif subcommand == "stats":
            return await self._show_stats()
        elif subcommand == "clear":
            return await self._clear_history()
        else:
            return (
                f"Unknown subcommand: {subcommand}\\n"
                f"Usage: {self.usage}\\n\\n"
                "Available subcommands:\\n"
                "  status  - Show current intelligence activity\\n"
                "  history - Show recent activity history\\n"
                "  stats   - Show activity statistics\\n"
                "  clear   - Clear activity history"
            )

    async def _show_status(self) -> str:
        """Show current intelligence activity status."""
        status_display = self.enhanced_console.status_display

        # Get current activity
        current = status_display.current_activity
        if not current:
            console.print("\\n[dim]No active intelligence operations[/dim]\\n")
            return ""

        # Create status panel
        content = f"[bold cyan]{current.activity.value.replace('_', ' ').title()}[/bold cyan]\\n\\n"
        content += f"📋 {current.get_display_text()}\\n"

        if current.details:
            content += "\\n[dim]Details:[/dim]\\n"
            for key, value in current.details.items():
                content += f"  • {key}: {value}\\n"

        elapsed = current.get_elapsed_time()
        content += f"\\n⏱️  Running for {elapsed:.1f}s"

        panel = Panel(
            content,
            title="🤖 Current Intelligence Activity",
            border_style="cyan",
            padding=(1, 2),
        )

        console.print("\\n")
        console.print(panel)
        console.print("\\n")

        return ""

    async def _show_history(self) -> str:
        """Show recent intelligence activity history."""
        # Use the enhanced console's show_intelligence_details method
        self.enhanced_console.show_intelligence_details()
        return ""

    async def _show_stats(self) -> str:
        """Show intelligence activity statistics."""
        summary = self.enhanced_console.get_intelligence_summary()

        # Create stats table
        table = Table(
            title="📊 Intelligence Activity Statistics",
            show_header=True,
            header_style="bold cyan",
            border_style="cyan",
        )
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="white", justify="right")

        # Current activity
        current_activity = summary.get("current_activity", "idle")
        table.add_row("Current Activity", current_activity.replace("_", " ").title())

        # Total activities
        total = summary.get("total_activities", 0)
        table.add_row("Total Activities", str(total))

        # Activity counts by type
        activity_counts = summary.get("activity_counts", {})
        if activity_counts:
            table.add_row("", "")  # Separator
            table.add_row("[bold]By Type[/bold]", "[bold]Count[/bold]")
            for activity, count in sorted(
                activity_counts.items(), key=lambda x: x[1], reverse=True
            ):
                table.add_row(
                    f"  {activity.replace('_', ' ').title()}", str(count), style="dim"
                )

        # Timing stats
        total_time = summary.get("total_time_seconds", 0.0)
        avg_time = summary.get("average_time_seconds", 0.0)

        table.add_row("", "")  # Separator
        table.add_row("Total Time", f"{total_time:.1f}s")
        table.add_row("Average Time", f"{avg_time:.1f}s")

        console.print("\\n")
        console.print(table)
        console.print("\\n")

        # Add memory stats if available
        if hasattr(self.agent, "memory"):
            memory = self.agent.memory
            memory_info = memory.get_summary()

            console.print(
                Panel(
                    memory_info,
                    title="🧠 Memory System",
                    border_style="blue",
                    padding=(1, 2),
                )
            )
            console.print("\\n")

        return ""

    async def _clear_history(self) -> str:
        """Clear intelligence activity history."""
        from rich.prompt import Confirm

        confirm = Confirm.ask(
            "\\n[yellow]Clear intelligence activity history?[/yellow]", default=False
        )

        if confirm:
            # Reset activity history
            self.enhanced_console.status_display.activity_history = []
            self.enhanced_console.status_display.current_activity = None
            console.print("\\n[green]✓ Intelligence history cleared[/green]\\n")
        else:
            console.print("\\n[dim]Cancelled[/dim]\\n")

        return ""
