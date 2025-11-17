"""
Enhanced error display for TUI.

Provides beautiful, user-friendly error messages with suggestions
and recovery options.
"""

import logging
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ..core.errors import (
    ContextLengthError,
    ErrorCategory,
    ErrorSeverity,
    GerdsenAIError,
    ModelNotFoundError,
    NetworkError,
    ProviderError,
    TimeoutError,
)

logger = logging.getLogger(__name__)
console = Console()


class ErrorDisplay:
    """
    Enhanced error display for TUI.

    Provides context-aware, beautiful error messages with actionable suggestions.
    """

    # Error severity colors
    SEVERITY_COLORS = {
        ErrorSeverity.LOW: "yellow",
        ErrorSeverity.MEDIUM: "orange1",
        ErrorSeverity.HIGH: "red",
        ErrorSeverity.CRITICAL: "bold red",
    }

    # Error category icons
    CATEGORY_ICONS = {
        ErrorCategory.NETWORK: "🌐",
        ErrorCategory.TIMEOUT: "⏱️",
        ErrorCategory.AUTH: "🔒",
        ErrorCategory.RATE_LIMIT: "🚦",
        ErrorCategory.MODEL_NOT_FOUND: "🤖",
        ErrorCategory.INVALID_REQUEST: "❌",
        ErrorCategory.CONTEXT_LENGTH: "📦",
        ErrorCategory.PROVIDER_ERROR: "⚠️",
        ErrorCategory.FILE_NOT_FOUND: "📁",
        ErrorCategory.PARSE_ERROR: "📝",
        ErrorCategory.CONFIGURATION: "⚙️",
        ErrorCategory.UNKNOWN: "❓",
    }

    @classmethod
    def display_error(
        cls,
        error: Exception,
        show_details: bool = False,
        tui_mode: bool = True
    ) -> str:
        """
        Display an error with rich formatting.

        Args:
            error: The error to display
            show_details: Show detailed error information
            tui_mode: Whether to use TUI formatting

        Returns:
            Formatted error string
        """
        if isinstance(error, GerdsenAIError):
            return cls._display_gerdsenai_error(error, show_details, tui_mode)
        else:
            return cls._display_generic_error(error, show_details, tui_mode)

    @classmethod
    def _display_gerdsenai_error(
        cls,
        error: GerdsenAIError,
        show_details: bool,
        tui_mode: bool
    ) -> str:
        """Display a GerdsenAI error with rich context."""
        icon = cls.CATEGORY_ICONS.get(error.category, "⚠️")
        color = cls.SEVERITY_COLORS.get(error.severity, "red")

        # Build message parts
        parts = []

        # Header with icon and category
        header = f"{icon} {error.category.value.upper()}"
        parts.append(f"[{color} bold]{header}[/]")

        # Error message
        parts.append(f"\n[{color}]{error.message}[/]")

        # Suggestion (if available)
        if error.suggestion:
            parts.append(f"\n💡 [cyan]Suggestion:[/] {error.suggestion}")

        # Recovery hint
        if error.recoverable:
            parts.append("\n[green]✓ This error is recoverable - retrying automatically[/]")
        else:
            parts.append("\n[red]✗ This error requires manual intervention[/]")

        # Context details (if requested)
        if show_details and error.context:
            parts.append("\n[dim]Details:[/]")
            for key, value in error.context.items():
                parts.append(f"  [dim]{key}:[/] {value}")

        # Original exception (if available and details requested)
        if show_details and error.original_exception:
            parts.append(f"\n[dim]Original error: {error.original_exception}[/]")

        message = "\n".join(parts)

        # Wrap in panel for TUI mode
        if tui_mode:
            return Panel(
                message,
                title=f"[{color}]Error Details[/]",
                border_style=color,
                expand=False
            )

        return message

    @classmethod
    def _display_generic_error(
        cls,
        error: Exception,
        show_details: bool,
        tui_mode: bool
    ) -> str:
        """Display a generic error."""
        error_type = type(error).__name__
        message = str(error)

        parts = [
            f"[red bold]{error_type}[/]",
            f"\n[red]{message}[/]",
        ]

        if show_details:
            parts.append(f"\n[dim]Type: {error_type}[/]")

        formatted = "\n".join(parts)

        if tui_mode:
            return Panel(
                formatted,
                title="[red]Error[/]",
                border_style="red",
                expand=False
            )

        return formatted

    @classmethod
    def get_recovery_actions(cls, error: GerdsenAIError) -> list[str]:
        """
        Get suggested recovery actions for an error.

        Args:
            error: The error to analyze

        Returns:
            List of recovery action strings
        """
        actions = []

        if error.category == ErrorCategory.NETWORK:
            actions.extend([
                "Check that the LLM server is running",
                "Verify network connectivity",
                "Check firewall settings",
                "Try a different provider (use /providers)",
            ])

        elif error.category == ErrorCategory.TIMEOUT:
            actions.extend([
                "Increase timeout in settings (/config)",
                "Use a faster model",
                "Reduce context length",
                "Check server performance",
            ])

        elif error.category == ErrorCategory.MODEL_NOT_FOUND:
            actions.extend([
                "List available models (/models)",
                "Pull the model if using Ollama",
                "Check model name spelling",
                "Select a different model (/model <name>)",
            ])

        elif error.category == ErrorCategory.CONTEXT_LENGTH:
            actions.extend([
                "Reduce context with /clear",
                "Use a model with larger context window",
                "Enable context compression in settings",
                "Summarize conversation (/compress)",
            ])

        elif error.category == ErrorCategory.PROVIDER_ERROR:
            actions.extend([
                "Check provider logs",
                "Restart the provider",
                "Try a different provider",
                "Update provider software",
            ])

        elif error.category == ErrorCategory.CONFIGURATION:
            actions.extend([
                "Review configuration (/config)",
                "Reset to defaults",
                "Check configuration file syntax",
                "Run setup wizard",
            ])

        else:
            actions.append("Check logs for more details")
            actions.append("Report issue if problem persists")

        return actions

    @classmethod
    def format_progress_message(
        cls,
        operation: str,
        progress: float,
        status: str = "",
        show_percentage: bool = True
    ) -> str:
        """
        Format a progress message.

        Args:
            operation: Operation name
            progress: Progress (0.0 to 1.0)
            status: Current status message
            show_percentage: Show percentage

        Returns:
            Formatted progress string
        """
        percentage = int(progress * 100)

        # Progress bar
        bar_width = 30
        filled = int(bar_width * progress)
        bar = "█" * filled + "░" * (bar_width - filled)

        parts = [f"[cyan]{operation}[/]"]

        if show_percentage:
            parts.append(f"[bold]{percentage}%[/]")

        parts.append(f"[{bar}]")

        if status:
            parts.append(f"[dim]{status}[/]")

        return " ".join(parts)

    @classmethod
    def format_success_message(cls, message: str, details: Optional[str] = None) -> str:
        """
        Format a success message.

        Args:
            message: Success message
            details: Optional details

        Returns:
            Formatted success string
        """
        parts = [f"[green bold]✓[/] [green]{message}[/]"]

        if details:
            parts.append(f"\n[dim]{details}[/]")

        return "\n".join(parts)

    @classmethod
    def format_warning_message(cls, message: str, suggestion: Optional[str] = None) -> str:
        """
        Format a warning message.

        Args:
            message: Warning message
            suggestion: Optional suggestion

        Returns:
            Formatted warning string
        """
        parts = [f"[yellow bold]⚠[/] [yellow]{message}[/]"]

        if suggestion:
            parts.append(f"\n[cyan]💡 {suggestion}[/]")

        return "\n".join(parts)

    @classmethod
    def format_info_message(cls, message: str, icon: str = "ℹ") -> str:
        """
        Format an info message.

        Args:
            message: Info message
            icon: Icon to use

        Returns:
            Formatted info string
        """
        return f"[blue]{icon}[/] [blue]{message}[/]"
