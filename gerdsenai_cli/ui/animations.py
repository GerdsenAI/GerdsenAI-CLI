"""
TUI animation system for status updates and progress indicators.

Provides:
- StatusAnimation: Animated status messages with various frame sequences
- AnimationFrames: Collection of predefined animation sequences
- PlanCapture: Extracts and formats AI plan summaries for approval
"""

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .prompt_toolkit_tui import PromptToolkitTUI

logger = logging.getLogger(__name__)


class AnimationFrames:
    """Collection of animation frame sequences."""

    SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    DOTS = ["   ", ".  ", ".. ", "..."]
    THINKING = ["🤔", "💭", "🤔", "💡"]
    PLANNING = ["📋", "📝", "✍️", "📊"]
    ANALYZING = ["🔍", "🔎", "🔬", "📊"]
    EXECUTING = ["⚡", "💫", "✨", "⚡"]


class StatusAnimation:
    """Manages animated status messages."""

    def __init__(self, tui: "PromptToolkitTUI", message: str, frames: list[str]):
        """Initialize status animation.

        Args:
            tui: PromptToolkitTUI instance
            message: Base message to display
            frames: List of animation frames
        """
        self.tui = tui
        self.message = message
        self.frames = frames
        self.running = False
        self.task: asyncio.Task | None = None
        self.frame_index = 0

    async def _animate(self):
        """Animation loop."""
        try:
            while self.running:
                frame = self.frames[self.frame_index % len(self.frames)]
                self.tui.status_text = f"{frame} {self.message}"
                self.tui.app.invalidate()
                self.frame_index += 1
                await asyncio.sleep(0.15)  # Animation speed
        except asyncio.CancelledError:
            pass

    def start(self):
        """Start the animation."""
        if not self.running:
            self.running = True
            self.frame_index = 0
            self.task = asyncio.create_task(self._animate())
            logger.debug(f"Started animation: {self.message}")

    def stop(self):
        """Stop the animation."""
        if self.running:
            self.running = False
            if self.task:
                self.task.cancel()
            logger.debug(f"Stopped animation: {self.message}")

    def update_message(self, message: str):
        """Update animation message while running."""
        self.message = message


class PlanCapture:
    """Captures and summarizes AI plan output."""

    @staticmethod
    def extract_summary(full_response: str) -> dict:
        """Extract key information from AI response.

        Args:
            full_response: Complete AI response text

        Returns:
            Dict with keys: summary, files_affected, actions, complexity, full_response
        """
        lines = full_response.split("\n")

        # Simple heuristics to extract plan information
        files_affected = []
        actions = []
        summary_lines = []

        for line in lines:
            line_lower = line.lower()

            # Extract file mentions
            if any(
                ext in line
                for ext in [
                    ".py",
                    ".js",
                    ".ts",
                    ".json",
                    ".md",
                    ".txt",
                    ".yml",
                    ".yaml",
                    ".toml",
                ]
            ):
                # Extract filename
                for word in line.split():
                    if any(
                        ext in word
                        for ext in [
                            ".py",
                            ".js",
                            ".ts",
                            ".json",
                            ".md",
                            ".txt",
                            ".yml",
                            ".yaml",
                            ".toml",
                        ]
                    ):
                        clean_word = word.strip("`,\"'()[]{}:;")
                        if clean_word and len(clean_word) > 3:
                            files_affected.append(clean_word)

            # Extract actions (lines mentioning key action verbs)
            if any(
                word in line_lower
                for word in [
                    "create",
                    "modify",
                    "delete",
                    "update",
                    "add",
                    "remove",
                    "implement",
                    "refactor",
                ]
            ):
                clean_line = line.strip()
                if (
                    clean_line
                    and len(clean_line) > 10
                    and not clean_line.startswith("#")
                ):
                    actions.append(clean_line)

            # Build summary (first few meaningful lines)
            if line.strip() and len(summary_lines) < 5:
                clean_line = line.strip()
                if not clean_line.startswith("#") and len(clean_line) > 20:
                    # Skip code blocks and common markers
                    if not any(
                        marker in clean_line for marker in ["```", "---", "===", "***"]
                    ):
                        summary_lines.append(clean_line)

        # Estimate complexity
        complexity = "simple"
        if len(files_affected) > 3 or len(actions) > 5:
            complexity = "complex"
        elif len(files_affected) > 1 or len(actions) > 2:
            complexity = "moderate"

        return {
            "summary": "\n".join(summary_lines[:3])
            if summary_lines
            else "AI planning response",
            "files_affected": list(dict.fromkeys(files_affected))[
                :10
            ],  # Dedupe and limit
            "actions": actions[:10],  # Limit to 10 actions
            "complexity": complexity,
            "full_response": full_response,
        }

    @staticmethod
    def format_plan_preview(plan: dict) -> str:
        """Format plan as user-friendly preview.

        Args:
            plan: Plan dict from extract_summary

        Returns:
            Formatted plan preview string
        """
        lines = [
            "📋 Plan Summary",
            "=" * 70,
            "",
            plan["summary"],
            "",
        ]

        if plan["files_affected"]:
            lines.append("📁 Files to be modified:")
            for file in plan["files_affected"]:
                lines.append(f"  • {file}")
            lines.append("")

        if plan["actions"]:
            lines.append("⚡ Actions:")
            for action in plan["actions"][:5]:  # Show first 5 actions
                lines.append(f"  • {action}")
            if len(plan["actions"]) > 5:
                lines.append(f"  ... and {len(plan['actions']) - 5} more actions")
            lines.append("")

        lines.extend(
            [
                f"Complexity: {plan['complexity'].upper()}",
                "",
                "━" * 70,
                "",
                "Do you want to proceed?",
                "  • Type 'yes' or 'approve' to execute this plan",
                "  • Type 'no' or 'cancel' to cancel",
                "  • Type 'show full' to see complete plan details",
            ]
        )

        return "\n".join(lines)
