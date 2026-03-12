"""
Core types and enums for GerdsenAI CLI.

Contains intelligence activity types used across the application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


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
