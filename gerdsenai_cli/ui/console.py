"""
Enhanced console with rich TUI layout and syntax highlighting.

Provides a modern, bordered interface for the GerdsenAI CLI.
"""

import re
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.live import Live
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML

from .layout import GerdsenAILayout
from .status_display import IntelligenceActivity, StatusDisplayManager
from ..utils.status_messages import OperationType, get_status_message


class EnhancedConsole:
    """Enhanced console with rich TUI capabilities."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize enhanced console.
        
        Args:
            console: Rich console instance (creates new if None)
        """
        self.console = console or Console()
        self.layout = GerdsenAILayout(self.console)
        self.use_tui: bool = True
        self.status_display = StatusDisplayManager(self.console)
        self._live: Optional[Live] = None  # Track active Live display
        self._persistent_live: Optional[Live] = None  # Persistent Live for full session
        self._prompt_session: Optional[PromptSession] = None  # For input in TUI mode

    def set_tui_mode(self, enabled: bool) -> None:
        """Enable or disable TUI mode.
        
        Args:
            enabled: Whether to use TUI layout
        """
        self.use_tui = enabled
    
    def start_persistent_tui(self) -> None:
        """Start persistent Live TUI that stays on screen for the entire session."""
        if self.use_tui and not self._persistent_live:
            # Initialize layout with empty state
            self.layout.update_input("")
            self.layout.update_response("", is_code=False)
            
            # Start persistent Live display
            self._persistent_live = Live(
                self.layout.layout,
                console=self.console,
                refresh_per_second=10,
                transient=False,
            )
            self._persistent_live.start()
            
            # Create prompt session for input
            self._prompt_session = PromptSession()
    
    def stop_persistent_tui(self) -> None:
        """Stop persistent Live TUI."""
        if self._persistent_live:
            self._persistent_live.stop()
            self._persistent_live = None
    
    async def get_input_in_tui(self) -> str:
        """Get user input while maintaining the TUI display.
        
        Returns:
            User input string
        """
        if not self._prompt_session:
            self._prompt_session = PromptSession()
        
        # Temporarily stop Live to allow input
        if self._persistent_live:
            self._persistent_live.stop()
        
        try:
            # Get input with styled prompt
            user_input = await self._prompt_session.prompt_async(
                HTML('<style fg="#00FFFF" bold="true">GerdsenAI</style><prompt> > </prompt>'),
                multiline=False,
            )
            
            # Update layout with user input
            self.layout.update_input(user_input)
            self.layout.update_response("", is_code=False)
            
            # Restart Live display
            if self.use_tui:
                self._persistent_live = Live(
                    self.layout.layout,
                    console=self.console,
                    refresh_per_second=10,
                    transient=False,
                )
                self._persistent_live.start()
            
            return user_input.strip()
        
        except (KeyboardInterrupt, EOFError):
            # Restart Live before raising
            if self.use_tui and not self._persistent_live:
                self._persistent_live = Live(
                    self.layout.layout,
                    console=self.console,
                    refresh_per_second=10,
                    transient=False,
                )
                self._persistent_live.start()
            raise

    def _detect_code_blocks(self, text: str) -> list[dict]:
        """Detect code blocks in markdown-formatted text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of code block info dicts with 'language', 'code', 'start', 'end'
        """
        # Match ```language\ncode\n``` patterns
        pattern = r"```(\w+)?\n(.*?)```"
        matches = re.finditer(pattern, text, re.DOTALL)
        
        blocks = []
        for match in matches:
            language = match.group(1) or "text"
            code = match.group(2).strip()
            blocks.append({
                "language": language,
                "code": code,
                "start": match.start(),
                "end": match.end(),
            })
        
        return blocks

    def _render_response_with_syntax(self, response: str) -> None:
        """Render response with syntax highlighting for code blocks.
        
        Args:
            response: The response text potentially containing code blocks
        """
        code_blocks = self._detect_code_blocks(response)
        
        if not code_blocks:
            # No code blocks, render as plain text
            if self.use_tui:
                self.layout.update_response(response, is_code=False)
            else:
                self.console.print(Markdown(response))
            return
        
        # For TUI mode, we need to display just the first code block
        # (since update_response only shows one block at a time)
        # For now, prioritize showing code blocks
        if self.use_tui and code_blocks:
            # Show the complete response as text (simpler for now)
            # TODO: Enhance to show multiple code blocks in sequence
            self.layout.update_response(response, is_code=False)
        else:
            # Non-TUI mode: Print each section separately
            last_end = 0
            for block in code_blocks:
                # Print text before code block
                if block["start"] > last_end:
                    text_before = response[last_end:block["start"]].strip()
                    if text_before:
                        self.console.print(text_before)
                
                # Print code block with syntax highlighting
                syntax = Syntax(
                    block["code"],
                    block["language"],
                    theme="monokai",
                    line_numbers=True,
                )
                self.console.print(syntax)
                
                last_end = block["end"]
            
            # Print remaining text after last code block
            if last_end < len(response):
                text_after = response[last_end:].strip()
                if text_after:
                    self.console.print(text_after)

    def print_message(
        self,
        user_input: str,
        ai_response: str,
    ) -> None:
        """Print a message exchange with automatic code detection.
        
        Args:
            user_input: User's input
            ai_response: AI's response (may contain code blocks)
        """
        if self.use_tui:
            self.layout.update_input(user_input)
            self._render_response_with_syntax(ai_response)
            self.layout.render()
        else:
            # Fallback to simple printing
            self.console.print(f"[bold green]You:[/bold green] {user_input}")
            self.console.print(f"[bold blue]GerdsenAI:[/bold blue]")
            self._render_response_with_syntax(ai_response)

    def start_streaming(self, user_input: str) -> None:
        """Start streaming response display.
        
        Args:
            user_input: User's input to display
        """
        if self.use_tui:
            # If persistent Live is active, just update the layout
            # Otherwise use temporary Live for streaming
            if self._persistent_live:
                self.layout.update_input(user_input)
                self.layout.update_response("", is_code=False)
                self._persistent_live.update(self.layout.layout)
            else:
                # Initialize layout for streaming
                self.layout.update_input(user_input)
                self.layout.update_response("", is_code=False)
                
                # Start Live display for in-place updates
                self._live = Live(
                    self.layout.layout,
                    console=self.console,
                    refresh_per_second=10,  # 10 updates per second for smooth streaming
                    transient=False,  # Keep the final output visible
                )
                self._live.start()
        else:
            self.console.print(f"[bold green]You:[/bold green] {user_input}")
            self.console.print("[bold blue]GerdsenAI:[/bold blue]", end=" ")

    def stream_chunk(self, chunk: str, accumulated_response: str) -> None:
        """Stream a chunk of the response.
        
        Args:
            chunk: The new chunk to display
            accumulated_response: Full response so far (including this chunk)
        """
        if self.use_tui:
            # Update TUI with accumulated response
            self.layout.update_response(accumulated_response, is_code=False)
            
            # Update the active Live display (persistent or temporary)
            if self._persistent_live:
                self._persistent_live.update(self.layout.layout)
            elif self._live:
                self._live.update(self.layout.layout)
        else:
            # Print chunk without newline for streaming effect
            self.console.print(chunk, end="", style="white")

    def finish_streaming(self) -> None:
        """Finish streaming response display."""
        if self.use_tui:
            # If using persistent Live, keep it running
            # Only stop temporary Live
            if self._live and not self._persistent_live:
                self._live.stop()
                self._live = None
                self.console.print()  # Add spacing after response
        else:
            self.console.print()  # Final newline for non-TUI mode

    def update_status(
        self,
        model: Optional[str] = None,
        context_files: Optional[int] = None,
        token_count: Optional[int] = None,
        current_task: Optional[str] = None,
        operation: Optional[str] = None,
    ) -> None:
        """Update status bar.
        
        Args:
            model: Current model name
            context_files: Number of context files
            token_count: Token count
            current_task: Current task description
            operation: Operation type (e.g., 'thinking', 'reading', 'analyzing')
        """
        # If operation is provided, generate a sophisticated status message
        if operation and operation.upper() in OperationType.__members__:
            op_type = OperationType[operation.upper()]
            current_task = get_status_message(op_type)
        
        if self.use_tui:
            self.layout.update_status(
                model=model,
                context_files=context_files,
                token_count=token_count,
                current_task=current_task,
            )
    
    def set_operation(self, operation: str) -> None:
        """Set current operation with sophisticated status message.
        
        Args:
            operation: Operation type (thinking, reading, analyzing, writing, planning,
                      searching, processing, streaming, contextualizing, synthesizing, evaluating)
        """
        self.update_status(operation=operation)

    def get_input(self, prompt: str = ">>> ") -> str:
        """Get user input.
        
        Args:
            prompt: Prompt text
            
        Returns:
            User input string
        """
        return Prompt.ask(prompt, console=self.console)

    def confirm(
        self,
        message: str,
        default: bool = False,
    ) -> bool:
        """Get confirmation from user.
        
        Args:
            message: Confirmation message
            default: Default value if user just presses Enter
            
        Returns:
            True if confirmed, False otherwise
        """
        return Confirm.ask(message, default=default, console=self.console)

    def clear(self) -> None:
        """Clear the console."""
        self.layout.clear()

    def print_error(self, message: str) -> None:
        """Print an error message.
        
        Args:
            message: Error message
        """
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def print_success(self, message: str) -> None:
        """Print a success message.
        
        Args:
            message: Success message
        """
        self.console.print(f"[bold green]Success:[/bold green] {message}")

    def print_info(self, message: str) -> None:
        """Print an info message.
        
        Args:
            message: Info message
        """
        self.console.print(f"[bold blue]Info:[/bold blue] {message}")

    def print_warning(self, message: str) -> None:
        """Print a warning message.
        
        Args:
            message: Warning message
        """
        self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")

    def set_intelligence_activity(
        self,
        activity: IntelligenceActivity,
        message: str,
        progress: float | None = None,
        details: dict | None = None,
        step_info: str | None = None,
    ) -> None:
        """Set current intelligence activity for display.

        Args:
            activity: Type of intelligence activity
            message: Display message
            progress: Optional progress (0.0 to 1.0)
            details: Optional activity details
            step_info: Optional step information (e.g., "Step 2/5")
        """
        self.status_display.set_activity(activity, message, progress, details, step_info)

        # Update layout with new status
        if self.use_tui:
            status_line = self.status_display.get_status_line()
            self.layout.update_status(current_task=status_line)

    def update_intelligence_progress(
        self, progress: float, step_info: str | None = None
    ) -> None:
        """Update progress of current intelligence activity.

        Args:
            progress: New progress value (0.0 to 1.0)
            step_info: Optional updated step information
        """
        self.status_display.update_progress(progress, step_info)

        if self.use_tui:
            status_line = self.status_display.get_status_line()
            self.layout.update_status(current_task=status_line)

    def clear_intelligence_activity(self) -> None:
        """Clear current intelligence activity."""
        self.status_display.clear_activity()

        if self.use_tui:
            self.layout.update_status(current_task="💤 Ready")

    def show_intelligence_details(self) -> None:
        """Show detailed intelligence activity history."""
        table = self.status_display.get_detailed_status()
        self.console.print("\n")
        self.console.print(table)
        self.console.print("\n")

    def get_intelligence_summary(self) -> dict:
        """Get summary of intelligence activity statistics.

        Returns:
            Dictionary with activity counts and timing info
        """
        return self.status_display.get_activity_summary()

    def show_clarifying_question(self, question) -> int | None:
        """
        Display a clarifying question with interpretations and get user choice.

        Args:
            question: ClarifyingQuestion object with interpretations

        Returns:
            Selected interpretation ID, or None if cancelled
        """
        from rich.panel import Panel
        from rich.table import Table

        # Show the question
        self.console.print()
        self.console.print(
            Panel(
                f"[yellow]{question.question}[/yellow]",
                title="Clarification Needed",
                border_style="yellow",
            )
        )

        # Create table of interpretations
        table = Table(
            title="Possible Interpretations",
            show_header=True,
            header_style="bold cyan",
            border_style="dim",
        )

        table.add_column("#", style="cyan", width=3)
        table.add_column("Interpretation", style="white", ratio=3)
        table.add_column("Confidence", style="dim", width=10)
        table.add_column("Details", style="dim", ratio=2)

        for interp in question.interpretations:
            confidence_bar = "█" * int(interp.confidence * 10)
            confidence_str = f"{confidence_bar} {interp.confidence:.0%}"

            details = interp.reasoning
            if interp.risks:
                details += f"\n[red]Risks: {', '.join(interp.risks)}[/red]"

            table.add_row(
                str(interp.id),
                f"[bold]{interp.title}[/bold]\n{interp.description}",
                confidence_str,
                details,
            )

        self.console.print(table)
        self.console.print()

        # Get user choice
        while True:
            choice_str = Prompt.ask(
                "Select an interpretation",
                choices=[str(i.id) for i in question.interpretations] + ["cancel"],
                default="1",
            )

            if choice_str.lower() == "cancel":
                return None

            try:
                choice_id = int(choice_str)
                # Validate choice
                if any(i.id == choice_id for i in question.interpretations):
                    return choice_id
            except ValueError:
                pass

            self.console.print("[red]Invalid choice. Please try again.[/red]")

    def show_clarification_stats(self, stats: dict) -> None:
        """
        Display clarification statistics.

        Args:
            stats: Statistics dictionary from ClarificationEngine
        """
        from rich.panel import Panel
        from rich.table import Table

        table = Table(title="Clarification Statistics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Total Clarifications", str(stats.get("total_clarifications", 0)))
        table.add_row(
            "Helpful Rate", f"{stats.get('helpful_rate', 0.0) * 100:.1f}%"
        )
        table.add_row("Most Common Type", str(stats.get("most_common_type", "N/A")))

        # Type breakdown
        if "type_breakdown" in stats:
            table.add_row("", "")  # Spacer
            table.add_row("[bold]Type Breakdown[/bold]", "")
            for type_name, count in stats["type_breakdown"].items():
                table.add_row(f"  {type_name}", str(count))

        self.console.print()
        self.console.print(Panel(table, border_style="cyan"))
        self.console.print()
