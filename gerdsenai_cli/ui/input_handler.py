"""
Enhanced input handler for GerdsenAI CLI using prompt_toolkit.

This module provides advanced terminal input features including autocompletion,
history management, and proper input/output separation.
"""

from pathlib import Path
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.styles import Style
from rich.console import Console

from ..commands.parser import CommandParser


class CommandCompleter(Completer):
    """Autocompletion for GerdsenAI commands and file paths."""

    def __init__(self, command_parser: Optional[CommandParser] = None):
        """Initialize the completer with command parser for command completion."""
        self.command_parser = command_parser
        self.console = Console()

    def get_completions(self, document, _complete_event):
        """Generate completions based on current input."""
        text = document.text

        if not text:
            return

        # Handle slash commands
        if text.startswith("/"):
            yield from self._complete_commands(text, document)
        else:
            # For non-command input, we could add file path completion later
            pass

    def _complete_commands(self, text: str, document):
        """Complete slash commands."""
        if not self.command_parser:
            return

        # Get available commands
        available_commands: list[str] = []
        registry = self.command_parser.registry
        for command in registry.commands.values():
            # Add main command
            available_commands.append(f"/{command.name}")
            # Add aliases
            for alias in command.aliases:
                available_commands.append(f"/{alias}")
        # Include standalone aliases
        for alias in registry.aliases:
            if alias not in registry.commands:
                available_commands.append(f"/{alias}")

        # Filter commands that start with current input
        current_command = text.lower()
        for command in available_commands:
            if command.lower().startswith(current_command):
                yield Completion(
                    command,
                    start_position=-len(text),
                    display=command[1:],  # Remove leading slash for display
                    style="class:completion",
                )


class EnhancedInputHandler:
    """Enhanced input handler with prompt_toolkit integration."""

    def __init__(
        self,
        command_parser: Optional[CommandParser] = None,
        history_file: Optional[Path] = None,
    ):
        """
        Initialize the enhanced input handler.

        Args:
            command_parser: Command parser for autocompletion
            history_file: Path to history file (defaults to ~/.gerdsenai_history)
        """
        self.command_parser = command_parser
        self.console = Console()

        # Set up history file
        if history_file is None:
            history_file = Path.home() / ".gerdsenai_history"

        # Create prompt session with enhanced features
        self.session = PromptSession(
            history=FileHistory(str(history_file)),
            completer=CommandCompleter(command_parser),
            complete_style=CompleteStyle.READLINE_LIKE,
            key_bindings=self._create_key_bindings(),
            style=self._create_style(),
        )

    def _create_key_bindings(self) -> KeyBindings:
        """Create custom key bindings for the input handler."""
        kb = KeyBindings()

        @kb.add("c-c")  # Ctrl+C
        def _(event):
            """Handle Ctrl+C - cancel current input."""
            event.app.exit(exception=KeyboardInterrupt())

        @kb.add("c-d")  # Ctrl+D
        def _(event):
            """Handle Ctrl+D - exit application if input is empty."""
            if not event.current_buffer.text:
                event.app.exit(exception=EOFError())
            else:
                event.current_buffer.delete_char()

        @kb.add("enter")
        def _(event):
            """Handle Enter - submit input."""
            event.current_buffer.validate_and_handle()

        return kb

    def _create_style(self) -> Style:
        """Create custom style for the prompt."""
        return Style.from_dict(
            {
                "prompt": "#00aa00 bold",
                "continuation": "#888888",
                "completion-menu.completion": "bg:#008888 #ffffff",
                "completion-menu.completion.current": "bg:#00aaaa #000000 bold",
                "completion-menu.meta.completion": "bg:#999999 #ffffff",
                "completion-menu.meta.completion.current": "bg:#aaaaaa #000000 bold",
                "scrollbar.background": "bg:#88aaaa",
                "scrollbar.button": "bg:#222222",
                "scrollbar.arrow": "bg:#222222",
            }
        )

    def _create_prompt_text(self) -> HTML:
        """Create the formatted prompt text."""
        return HTML(
            '<prompt>[AI] </prompt><style fg="#00FFFF" bold="true">GerdsenAI</style><prompt> > </prompt>'
        )

    async def get_user_input(self) -> str:
        """
        Get user input with enhanced features.

        Returns:
            User input string

        Raises:
            KeyboardInterrupt: On Ctrl+C
            EOFError: On Ctrl+D with empty input (exit signal)
        """
        try:
            # Get input asynchronously
            result = await self.session.prompt_async(
                self._create_prompt_text(),
                multiline=False,
                wrap_lines=True,
            )
            return result.strip()

        except KeyboardInterrupt:
            # User pressed Ctrl+C
            self.console.print("\n[dim]Input cancelled[/dim]")
            raise

        except EOFError:
            # User pressed Ctrl+D on empty input (exit signal)
            raise

    def update_command_parser(self, command_parser: CommandParser) -> None:
        """Update the command parser for autocompletion."""
        self.command_parser = command_parser
        completer = self.session.completer
        if isinstance(completer, CommandCompleter):
            completer.command_parser = command_parser

    def add_to_history(self, text: str) -> None:
        """Add text to command history."""
        if text.strip():
            self.session.history.append_string(text)

    async def cleanup(self) -> None:
        """Clean up resources."""
        # Save history
        history = getattr(self.session, "history", None)
        if history and hasattr(history, "save"):
            history.save()


class InputHandlerError(Exception):
    """Exception raised by input handler."""

    pass
