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

from .layout import GerdsenAILayout


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

    def set_tui_mode(self, enabled: bool) -> None:
        """Enable or disable TUI mode.
        
        Args:
            enabled: Whether to use TUI layout
        """
        self.use_tui = enabled

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
            self.layout.update_input(user_input)
            self.layout.update_response("", is_code=False)
            self.layout.render()
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
            self.layout.render()
        else:
            # Print chunk without newline for streaming effect
            self.console.print(chunk, end="", style="white")

    def finish_streaming(self) -> None:
        """Finish streaming response display."""
        if not self.use_tui:
            self.console.print()  # Final newline for non-TUI mode

    def update_status(
        self,
        model: Optional[str] = None,
        context_files: Optional[int] = None,
        token_count: Optional[int] = None,
        current_task: Optional[str] = None,
    ) -> None:
        """Update status bar.
        
        Args:
            model: Current model name
            context_files: Number of context files
            token_count: Token count
            current_task: Current task description
        """
        if self.use_tui:
            self.layout.update_status(
                model=model,
                context_files=context_files,
                token_count=token_count,
                current_task=current_task,
            )

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
