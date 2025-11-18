"""
Undo command implementation for GerdsenAI CLI.

Provides /undo command for reverting recent operations.
"""

import logging

from .base import BaseCommand, CommandCategory

logger = logging.getLogger(__name__)


class UndoCommand(BaseCommand):
    """Command for undoing recent operations."""

    name = "undo"
    description = "Undo the last operation (restores from snapshot)"
    category = CommandCategory.AGENT
    usage = "/undo [list|clear|help]"

    async def execute(self, args: list[str]) -> str:
        """
        Execute undo command.

        Args:
            args: Command arguments

        Returns:
            Result message
        """
        if not hasattr(self.agent, "confirmation_engine"):
            return "Error: Confirmation engine not initialized"

        confirmation_engine = self.agent.confirmation_engine

        # Parse subcommand
        subcommand = args[0] if args else "undo"

        if subcommand == "list":
            return await self._list_snapshots(confirmation_engine)

        elif subcommand == "clear":
            return await self._clear_snapshots(confirmation_engine)

        elif subcommand == "help":
            return self._show_help()

        else:
            # Default: undo last operation
            return await self._undo_last(confirmation_engine)

    async def _undo_last(self, confirmation_engine) -> str:
        """
        Undo the last operation.

        Args:
            confirmation_engine: ConfirmationEngine instance

        Returns:
            Result message
        """
        snapshots = confirmation_engine.list_undo_snapshots()

        if not snapshots:
            return "No operations to undo.\n\nUse /undo list to see available snapshots."

        # Get most recent snapshot
        latest = snapshots[0]

        # Show what will be undone
        if self.console:
            from rich.panel import Panel

            self.console.console.print()
            self.console.console.print(
                Panel(
                    f"[bold]Operation:[/bold] {latest.description}\n"
                    f"[bold]Type:[/bold] {latest.operation_type.value}\n"
                    f"[bold]Affected Files:[/bold] {len(latest.affected_files)}\n"
                    f"[bold]Timestamp:[/bold] {latest.timestamp}\n"
                    f"[bold]Risk Level:[/bold] {latest.metadata.get('risk_level', 'unknown')}",
                    title="Undo Preview",
                    border_style="yellow",
                )
            )

            # Confirm
            response = input("\nProceed with undo? (yes/no): ").strip().lower()

            if response not in ["y", "yes"]:
                return "Undo cancelled."

        # Perform undo
        success, message = confirmation_engine.undo_last_operation()

        # Display result
        if self.console:
            files_restored = len(latest.affected_files) if success else 0
            self.console.show_undo_result(success, message, files_restored)
            return ""  # Message already displayed
        else:
            return message

    async def _list_snapshots(self, confirmation_engine) -> str:
        """
        List available undo snapshots.

        Args:
            confirmation_engine: ConfirmationEngine instance

        Returns:
            Result message
        """
        snapshots = confirmation_engine.list_undo_snapshots()

        if self.console:
            self.console.show_undo_snapshots(snapshots)
            return ""  # Message already displayed
        else:
            if not snapshots:
                return "No undo snapshots available"

            lines = ["Available Undo Snapshots:", ""]
            for i, snapshot in enumerate(snapshots, 1):
                lines.append(
                    f"{i}. {snapshot.snapshot_id} - {snapshot.description} "
                    f"({len(snapshot.affected_files)} file(s), {snapshot.timestamp.split('T')[0]})"
                )

            return "\n".join(lines)

    async def _clear_snapshots(self, confirmation_engine) -> str:
        """
        Clear all undo snapshots.

        Args:
            confirmation_engine: ConfirmationEngine instance

        Returns:
            Result message
        """
        snapshots = confirmation_engine.list_undo_snapshots()

        if not snapshots:
            return "No undo snapshots to clear."

        # Confirm clearing
        if self.console:
            from rich.panel import Panel

            self.console.console.print()
            self.console.console.print(
                Panel(
                    f"[bold yellow]⚠ Warning:[/bold yellow]\n\n"
                    f"This will permanently delete all {len(snapshots)} undo snapshot(s).\n"
                    f"This action cannot be undone.",
                    title="Clear Undo History",
                    border_style="red",
                )
            )

            response = input("\nProceed with clearing? (yes/no): ").strip().lower()

            if response not in ["y", "yes"]:
                return "Clear cancelled."

        # Clear snapshots
        count, bytes_freed = confirmation_engine.clear_undo_history()

        # Format bytes freed
        if bytes_freed > 1024 * 1024:
            size_str = f"{bytes_freed / (1024 * 1024):.2f} MB"
        elif bytes_freed > 1024:
            size_str = f"{bytes_freed / 1024:.2f} KB"
        else:
            size_str = f"{bytes_freed} bytes"

        return f"Cleared {count} undo snapshot(s), freed {size_str}"

    def _show_help(self) -> str:
        """
        Show help for undo command.

        Returns:
            Help text
        """
        return """Undo Command

Usage:
  /undo          - Undo the last operation (prompts for confirmation)
  /undo list     - List all available undo snapshots
  /undo clear    - Clear all undo snapshots (frees disk space)
  /undo help     - Show this help message

Description:
  The undo system automatically creates snapshots before high-risk operations.
  Snapshots are retained for 24 hours and include file backups.

Examples:
  /undo                # Undo the most recent operation
  /undo list           # See all available undo points
  /undo clear          # Remove all undo snapshots

Notes:
  - Snapshots expire after 24 hours
  - Maximum of 50 snapshots retained
  - Only operations with file changes can be undone
  - Undo is not available for operations that didn't create snapshots
"""
