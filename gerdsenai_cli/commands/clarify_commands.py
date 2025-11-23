"""
Clarification commands for GerdsenAI CLI.

Provides commands to manage and view clarification settings and statistics.
"""

from .base import BaseCommand


class ClarifyCommand(BaseCommand):
    """Show clarification statistics and manage clarification settings."""

    name = "clarify"
    description = "Show clarification statistics or adjust settings"
    usage = "/clarify [stats|threshold <value>|reset]"

    async def execute(self, args: list[str]) -> str:
        """
        Execute the clarify command.

        Args:
            args: Command arguments

        Returns:
            Command output message
        """
        if not self.agent:
            return "Error: Agent not available"

        # Default: show stats
        if not args or args[0] == "stats":
            return await self._show_stats()

        elif args[0] == "threshold":
            if len(args) < 2:
                return "Usage: /clarify threshold <value>\nValue should be between 0.0 and 1.0"
            return await self._set_threshold(args[1])

        elif args[0] == "reset":
            return await self._reset_history()

        elif args[0] == "help":
            return self._show_help()

        else:
            return f"Unknown subcommand: {args[0]}\nUse '/clarify help' for usage information"

    async def _show_stats(self) -> str:
        """Show clarification statistics."""
        if not hasattr(self.agent, "clarification"):
            return "Clarification system not available"

        stats = self.agent.clarification.get_stats()

        if self.console:
            self.console.show_clarification_stats(stats)
            return ""  # Stats are shown via console method

        # Fallback to text output
        output = "\nClarification Statistics\n"
        output += "=" * 40 + "\n\n"
        output += f"Total clarifications: {stats['total_clarifications']}\n"
        output += f"Helpful rate: {stats['helpful_rate'] * 100:.1f}%\n"
        output += f"Most common type: {stats.get('most_common_type', 'N/A')}\n"

        if stats.get("type_breakdown"):
            output += "\nType Breakdown:\n"
            for type_name, count in stats["type_breakdown"].items():
                output += f"  {type_name}: {count}\n"

        return output

    async def _set_threshold(self, value_str: str) -> str:
        """Set the clarification confidence threshold."""
        try:
            threshold = float(value_str)

            if not 0.0 <= threshold <= 1.0:
                return "Error: Threshold must be between 0.0 and 1.0"

            # Update in settings
            self.agent.settings.set_preference(
                "clarification_confidence_threshold", threshold
            )

            # Update in clarification engine
            if hasattr(self.agent, "clarification"):
                self.agent.clarification.confidence_threshold = threshold

            return (
                f"Clarification threshold updated to {threshold:.2f}\n\n"
                f"Requests with confidence below {threshold:.0%} will trigger clarification."
            )

        except ValueError:
            return f"Error: Invalid threshold value: {value_str}\nMust be a number between 0.0 and 1.0"

    async def _reset_history(self) -> str:
        """Reset clarification history."""
        if not hasattr(self.agent, "clarification"):
            return "Clarification system not available"

        from rich.prompt import Confirm

        # Confirm reset
        if self.console:
            confirmed = Confirm.ask(
                "[yellow]Are you sure you want to reset clarification history?[/yellow]",
                default=False,
            )
        else:
            confirmed = input("Reset clarification history? (y/N): ").lower() == "y"

        if not confirmed:
            return "Reset cancelled"

        # Clear history
        old_count = len(self.agent.clarification.history)
        self.agent.clarification.history.clear()
        self.agent.clarification._save_history()

        return f"Cleared {old_count} clarification records from history"

    def _show_help(self) -> str:
        """Show help for clarify command."""
        return """
Clarify Command Help
==================

The /clarify command manages the clarification system, which asks questions
when the agent is uncertain about your intent.

Subcommands:
  stats              Show clarification statistics
  threshold <value>  Set confidence threshold (0.0-1.0)
  reset              Clear clarification history
  help               Show this help message

Examples:
  /clarify                    # Show statistics
  /clarify stats              # Show statistics
  /clarify threshold 0.6      # Set threshold to 0.6
  /clarify reset              # Clear history

About Thresholds:
  The threshold determines when clarification is triggered.
  - Lower values (e.g., 0.5) = More clarifications
  - Higher values (e.g., 0.8) = Fewer clarifications
  - Default: 0.7 (70% confidence)

  When the agent's confidence is below the threshold, it will ask
  for clarification instead of guessing your intent.
"""


__all__ = ["ClarifyCommand"]
