"""
Advanced status display for TUI integration.

Provides real-time visual feedback for agent intelligence operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from rich.console import Console
from rich.table import Table


class IntelligenceActivity(Enum):
    """Types of intelligence activities to display."""

    IDLE = "idle"
    PLANNING = "planning"
    ANALYZING_CONTEXT = "analyzing_context"
    RECALLING_MEMORY = "recalling_memory"
    DETECTING_INTENT = "detecting_intent"
    GENERATING_SUGGESTIONS = "generating_suggestions"
    ASKING_CLARIFICATION = "asking_clarification"
    EXECUTING_PLAN = "executing_plan"
    CONFIRMING_OPERATION = "confirming_operation"
    THINKING = "thinking"
    READING_FILES = "reading_files"
    WRITING_CODE = "writing_code"


@dataclass
class ActivityStatus:
    """Current status of an intelligence activity."""

    activity: IntelligenceActivity
    message: str
    progress: float | None = None  # 0.0 to 1.0
    details: dict[str, Any] | None = None
    started_at: datetime = field(default_factory=datetime.now)
    step_info: str | None = None  # e.g., "Step 2/5" for planning

    def get_display_text(self) -> str:
        """Get formatted display text for this activity."""
        icon = self._get_icon()

        # Build base message
        parts = [icon, self.message]

        # Add step info if available
        if self.step_info:
            parts.append(f"[{self.step_info}]")

        # Add progress percentage if available
        if self.progress is not None:
            progress_percent = int(self.progress * 100)
            parts.append(f"({progress_percent}%)")

        return " ".join(parts)

    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds since activity started."""
        delta = datetime.now() - self.started_at
        return delta.total_seconds()

    def _get_icon(self) -> str:
        """Get icon for activity type."""
        icons = {
            IntelligenceActivity.IDLE: "💤",
            IntelligenceActivity.PLANNING: "📋",
            IntelligenceActivity.ANALYZING_CONTEXT: "🔍",
            IntelligenceActivity.RECALLING_MEMORY: "🧠",
            IntelligenceActivity.DETECTING_INTENT: "🎯",
            IntelligenceActivity.GENERATING_SUGGESTIONS: "💡",
            IntelligenceActivity.ASKING_CLARIFICATION: "❓",
            IntelligenceActivity.EXECUTING_PLAN: "⚡",
            IntelligenceActivity.CONFIRMING_OPERATION: "⚠️",
            IntelligenceActivity.THINKING: "🤔",
            IntelligenceActivity.READING_FILES: "📖",
            IntelligenceActivity.WRITING_CODE: "✍️",
        }
        return icons.get(self.activity, "🤖")


class StatusDisplayManager:
    """Manages status display for intelligence operations."""

    def __init__(self, console: Console | None = None):
        """Initialize status display manager.

        Args:
            console: Rich console for output (creates new if None)
        """
        self.console = console or Console()
        self.current_activity: ActivityStatus | None = None
        self.activity_history: list[ActivityStatus] = []
        self.max_history = 10

    def set_activity(
        self,
        activity: IntelligenceActivity,
        message: str,
        progress: float | None = None,
        details: dict[str, Any] | None = None,
        step_info: str | None = None,
    ) -> None:
        """Set current activity status.

        Args:
            activity: Type of activity
            message: Display message
            progress: Optional progress (0.0 to 1.0)
            details: Optional activity details
            step_info: Optional step information (e.g., "Step 2/5")
        """
        status = ActivityStatus(
            activity=activity,
            message=message,
            progress=progress,
            details=details,
            started_at=datetime.now(),
            step_info=step_info,
        )

        # Archive current activity to history before replacing
        if (
            self.current_activity
            and self.current_activity.activity != IntelligenceActivity.IDLE
        ):
            self.activity_history.append(self.current_activity)

            # Trim history
            if len(self.activity_history) > self.max_history:
                self.activity_history = self.activity_history[-self.max_history :]

        self.current_activity = status

    def update_progress(self, progress: float, step_info: str | None = None) -> None:
        """Update progress of current activity.

        Args:
            progress: New progress value (0.0 to 1.0)
            step_info: Optional updated step information
        """
        if self.current_activity:
            self.current_activity.progress = progress
            if step_info is not None:
                self.current_activity.step_info = step_info

    def clear_activity(self) -> None:
        """Clear current activity."""
        if (
            self.current_activity
            and self.current_activity.activity != IntelligenceActivity.IDLE
        ):
            self.activity_history.append(self.current_activity)

            # Trim history
            if len(self.activity_history) > self.max_history:
                self.activity_history = self.activity_history[-self.max_history :]

        self.current_activity = None

    def get_status_line(self) -> str:
        """Get single-line status for footer display.

        Returns:
            Formatted status line
        """
        if not self.current_activity:
            return "💤 Ready"

        return self.current_activity.get_display_text()

    def get_detailed_status(self) -> Table:
        """Get detailed status table for expanded view.

        Returns:
            Rich table with activity details
        """
        table = Table(
            title="🤖 Intelligence Activity",
            show_header=True,
            header_style="bold cyan",
            border_style="cyan",
        )
        table.add_column("Activity", style="cyan", no_wrap=True)
        table.add_column("Status", style="white")
        table.add_column("Time", style="dim", justify="right")

        # Current activity
        if self.current_activity:
            elapsed = f"{self.current_activity.get_elapsed_time():.1f}s"

            table.add_row(
                self.current_activity.activity.value.replace("_", " ").title(),
                self.current_activity.get_display_text(),
                elapsed,
                style="bold green",
            )

        # Recent history (most recent first)
        for status in reversed(self.activity_history[-5:]):
            if status != self.current_activity:
                # Calculate elapsed time from start to now
                elapsed = f"{status.get_elapsed_time():.1f}s ago"

                table.add_row(
                    status.activity.value.replace("_", " ").title(),
                    status.message,
                    elapsed,
                    style="dim",
                )

        if not self.current_activity and not self.activity_history:
            table.add_row("Idle", "No recent activity", "-", style="dim")

        return table

    def get_activity_summary(self) -> dict[str, Any]:
        """Get summary of activity statistics.

        Returns:
            Dictionary with activity counts and timing info
        """
        activity_counts: dict[str, int] = {}
        total_time = 0.0

        for status in self.activity_history:
            activity_name = status.activity.value
            activity_counts[activity_name] = activity_counts.get(activity_name, 0) + 1
            total_time += status.get_elapsed_time()

        return {
            "current_activity": (
                self.current_activity.activity.value
                if self.current_activity
                else "idle"
            ),
            "total_activities": len(self.activity_history),
            "activity_counts": activity_counts,
            "total_time_seconds": total_time,
            "average_time_seconds": (
                total_time / len(self.activity_history)
                if self.activity_history
                else 0.0
            ),
        }
