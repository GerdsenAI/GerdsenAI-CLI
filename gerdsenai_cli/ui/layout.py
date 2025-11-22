"""
Enhanced TUI layout system for GerdsenAI CLI.

Provides a rich, bordered interface similar to modern AI coding assistants.
"""


from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text


class GerdsenAILayout:
    """Manages the TUI layout with multiple panels."""

    def __init__(self, console: Console):
        """Initialize the layout manager.

        Args:
            console: Rich console instance
        """
        self.console = console
        self.layout = Layout()
        self._setup_layout()
        self.current_model: str | None = None
        self.context_files: int = 0
        self.token_count: int = 0

    def _setup_layout(self) -> None:
        """Set up the initial layout structure.

        Layout structure:
        ┌─────────────────────────────────────────┐
        │ GerdsenAI Response (expandable)         │
        │                                         │
        ├─────────────────────────────────────────┤
        │ Footer: task | tokens | context | model│
        ├─────────────────────────────────────────┤
        │ You: (2-3 lines, compact input)         │
        └─────────────────────────────────────────┘
        """
        # Create main layout with response, footer, and input
        self.layout.split(
            Layout(name="response", ratio=1),  # Main response area (expandable)
            Layout(name="footer", size=3),  # Status/info bar
            Layout(name="input", size=5),  # Compact input area (2-3 lines visible)
        )

    def update_status(
        self,
        model: str | None = None,
        context_files: int | None = None,
        token_count: int | None = None,
        current_task: str | None = None,
    ) -> None:
        """Update the status bar information.

        Args:
            model: Current model name
            context_files: Number of files in context
            token_count: Current token count
            current_task: Current task description
        """
        if model is not None:
            self.current_model = model
        if context_files is not None:
            self.context_files = context_files
        if token_count is not None:
            self.token_count = token_count
        if current_task is not None:
            self.current_task = current_task

        # Build status text with task, tokens, context, model
        status_parts = []

        # Task info (e.g., "Sublimating... (esc to interrupt · ctrl+t to show todos · 34s · ↓ 9.6k tokens)")
        if hasattr(self, "current_task") and self.current_task:
            status_parts.append(f"Task: {self.current_task}")

        if self.token_count > 0:
            # Format token count nicely (e.g., "9.6k tokens")
            if self.token_count >= 1000:
                token_display = f"{self.token_count / 1000:.1f}k"
            else:
                token_display = str(self.token_count)
            status_parts.append(f"↓ {token_display} tokens")

        if self.context_files > 0:
            status_parts.append(f"Context: {self.context_files} files")

        if self.current_model:
            # Shorten model name if it's long
            model_display = (
                self.current_model.split("/")[-1]
                if "/" in self.current_model
                else self.current_model
            )
            if len(model_display) > 30:
                model_display = model_display[:27] + "..."
            status_parts.append(f"Model: {model_display}")

        status_text = " · ".join(status_parts) if status_parts else "Ready"

        self.layout["footer"].update(
            Panel(
                Text(status_text, style="dim white", justify="left"),
                style="dim",
                border_style="dim",
            )
        )

    def update_input(self, user_input: str, max_preview_lines: int = 3) -> None:
        """Update the input panel with user's message (compact, 2-3 lines).

        For large blocks of text/code, shows a preview with indicator of hidden content.

        Args:
            user_input: The user's input text
            max_preview_lines: Maximum lines to show before truncating
        """
        lines = user_input.split("\n")

        if len(lines) > max_preview_lines:
            # Large block - show preview with indicator
            preview_lines = lines[:max_preview_lines]
            preview_text = "\n".join(preview_lines)
            content = Text()
            content.append(preview_text, style="white")
            content.append(f"\n[pasted text {len(lines)} rows]", style="dim yellow")
        else:
            # Small input - show all
            content = Text(user_input, style="white")

        self.layout["input"].update(
            Panel(
                content,
                title="[bold green]You[/bold green]",
                border_style="green",
                height=5,  # Keep compact (2-3 visible lines + border)
            )
        )

    def update_response(
        self, response: str, is_code: bool = False, language: str = "python"
    ) -> None:
        """Update the response panel with AI's message.

        Args:
            response: The AI's response text
            is_code: Whether the response is code (for syntax highlighting)
            language: Programming language for syntax highlighting
        """
        if is_code:
            # Syntax highlight code responses
            syntax = Syntax(
                response,
                language,
                theme="monokai",
                line_numbers=True,
                word_wrap=True,
            )
            content = syntax
        else:
            content = Text(response, style="white")

        self.layout["response"].update(
            Panel(
                content,
                title="[bold cyan]GerdsenAI[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),  # Add padding for readability
            )
        )

    def render(self) -> None:
        """Render the current layout to the console."""
        self.console.print(self.layout)

    def clear(self) -> None:
        """Clear the console."""
        self.console.clear()


class LiveTUI:
    """Live-updating TUI for real-time feedback."""

    def __init__(self, console: Console):
        """Initialize live TUI.

        Args:
            console: Rich console instance
        """
        self.console = console
        self.layout = GerdsenAILayout(console)
        self.live: Live | None = None

    def __enter__(self):
        """Start the live display."""
        self.live = Live(
            self.layout.layout,
            console=self.console,
            refresh_per_second=4,
            screen=False,
        )
        self.live.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the live display."""
        if self.live:
            self.live.__exit__(exc_type, exc_val, exc_tb)

    def update(self) -> None:
        """Force a refresh of the display."""
        if self.live:
            self.live.refresh()
