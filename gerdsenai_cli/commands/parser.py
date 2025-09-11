"""
Command parser and routing system for GerdsenAI CLI.

This module provides the central command parsing and routing functionality,
including command registration, discovery, and execution management.
"""

import inspect
import re
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from ..utils.display import show_error, show_info, show_warning
from .base import BaseCommand, CommandCategory, CommandResult

console = Console()


class CommandRegistry:
    """Registry for managing CLI commands."""

    def __init__(self):
        """Initialize command registry."""
        self.commands: dict[str, BaseCommand] = {}
        self.aliases: dict[str, str] = {}  # alias -> command_name
        self.categories: dict[CommandCategory, list[str]] = {}

        # Initialize categories
        for category in CommandCategory:
            self.categories[category] = []

    def register(self, command: BaseCommand) -> None:
        """
        Register a command in the registry.

        Args:
            command: Command instance to register
        """
        if command.name in self.commands:
            raise ValueError(f"Command '{command.name}' is already registered")

        # Register main command
        self.commands[command.name] = command

        # Register aliases
        for alias in command.aliases:
            if alias in self.aliases or alias in self.commands:
                raise ValueError(
                    f"Alias '{alias}' conflicts with existing command or alias"
                )
            self.aliases[alias] = command.name

        # Add to category
        if command.category not in self.categories:
            self.categories[command.category] = []
        self.categories[command.category].append(command.name)

        show_info(f"Registered command: /{command.name}")

    def unregister(self, command_name: str) -> bool:
        """
        Unregister a command from the registry.

        Args:
            command_name: Name of command to unregister

        Returns:
            True if command was unregistered, False if not found
        """
        if command_name not in self.commands:
            return False

        command = self.commands[command_name]

        # Remove from commands
        del self.commands[command_name]

        # Remove aliases
        aliases_to_remove = [
            alias for alias, name in self.aliases.items() if name == command_name
        ]
        for alias in aliases_to_remove:
            del self.aliases[alias]

        # Remove from category
        if command.category in self.categories:
            self.categories[command.category] = [
                name
                for name in self.categories[command.category]
                if name != command_name
            ]

        return True

    def get_command(self, name: str) -> BaseCommand | None:
        """
        Get command by name or alias.

        Args:
            name: Command name or alias

        Returns:
            Command instance or None if not found
        """
        # Check direct command name
        if name in self.commands:
            return self.commands[name]

        # Check aliases
        if name in self.aliases:
            return self.commands[self.aliases[name]]

        return None

    def list_commands(
        self, category: CommandCategory | None = None
    ) -> list[BaseCommand]:
        """
        List registered commands, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of command instances
        """
        if category is None:
            return list(self.commands.values())

        command_names = self.categories.get(category, [])
        return [self.commands[name] for name in command_names]

    def get_all_names(self) -> set[str]:
        """Get all command names and aliases."""
        names = set(self.commands.keys())
        names.update(self.aliases.keys())
        return names


class CommandParser:
    """Main command parser and execution engine."""

    def __init__(self):
        """Initialize command parser."""
        self.registry = CommandRegistry()
        self.execution_context: dict[str, Any] = {}

        # Command pattern for parsing
        self.command_pattern = re.compile(r"^/([a-zA-Z][a-zA-Z0-9_-]*)\s*(.*?)$")

    def set_context(self, context: dict[str, Any]) -> None:
        """
        Set execution context for commands.

        Args:
            context: Context dictionary with app state, agent, etc.
        """
        self.execution_context = context

    def update_context(self, updates: dict[str, Any]) -> None:
        """
        Update execution context.

        Args:
            updates: Dictionary of context updates
        """
        self.execution_context.update(updates)

    def register_command(self, command: BaseCommand) -> None:
        """
        Register a command.

        Args:
            command: Command to register
        """
        self.registry.register(command)

    def register_commands(self, commands: list[BaseCommand]) -> None:
        """
        Register multiple commands.

        Args:
            commands: List of commands to register
        """
        for command in commands:
            self.register_command(command)

    def is_command(self, input_text: str) -> bool:
        """
        Check if input text is a command.

        Args:
            input_text: Input text to check

        Returns:
            True if input is a command
        """
        return input_text.strip().startswith("/")

    def parse_command(self, input_text: str) -> tuple[str, str] | None:
        """
        Parse command from input text.

        Args:
            input_text: Input text containing command

        Returns:
            Tuple of (command_name, arguments) or None if not a command
        """
        match = self.command_pattern.match(input_text.strip())
        if match:
            command_name = match.group(1)
            args_text = match.group(2)
            return command_name, args_text
        return None

    async def execute_command(self, input_text: str) -> CommandResult:
        """
        Parse and execute a command.

        Args:
            input_text: Command input text

        Returns:
            CommandResult from execution
        """
        # Parse command
        parsed = self.parse_command(input_text)
        if not parsed:
            return CommandResult(
                success=False,
                message="Invalid command format. Commands must start with '/' followed by command name.",
            )

        command_name, args_text = parsed

        # Get command
        command = self.registry.get_command(command_name)
        if not command:
            # Try to suggest similar commands
            suggestions = self._get_command_suggestions(command_name)
            suggestion_text = ""
            if suggestions:
                suggestion_text = (
                    f"\n\nDid you mean: {', '.join(f'/{s}' for s in suggestions)}"
                )

            return CommandResult(
                success=False,
                message=f"Unknown command: /{command_name}{suggestion_text}\n\nType /help to see available commands.",
            )

        # Execute command
        try:
            result = await command.run(args_text, self.execution_context)
            return result
        except Exception as e:
            return CommandResult(
                success=False, message=f"Command execution failed: {e}"
            )

    def _get_command_suggestions(
        self, command_name: str, max_suggestions: int = 3
    ) -> list[str]:
        """
        Get command suggestions based on similarity.

        Args:
            command_name: Invalid command name
            max_suggestions: Maximum number of suggestions

        Returns:
            List of suggested command names
        """
        all_names = self.registry.get_all_names()
        suggestions = []

        # Simple similarity based on string distance
        for name in all_names:
            if self._string_similarity(command_name.lower(), name.lower()) > 0.6:
                suggestions.append(name)

        # Sort by similarity and return top suggestions
        suggestions.sort(
            key=lambda x: self._string_similarity(command_name.lower(), x.lower()),
            reverse=True,
        )
        return suggestions[:max_suggestions]

    def _string_similarity(self, s1: str, s2: str) -> float:
        """
        Calculate simple string similarity.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Similarity score between 0 and 1
        """
        if not s1 or not s2:
            return 0.0

        # Simple Levenshtein-like similarity
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0

        # Count matching characters
        matches = sum(1 for c1, c2 in zip(s1, s2, strict=False) if c1 == c2)
        return matches / max_len

    def show_help(self, command_name: str | None = None) -> None:
        """
        Show help for specific command or all commands.

        Args:
            command_name: Optional specific command to show help for
        """
        if command_name:
            # Show help for specific command
            command = self.registry.get_command(command_name)
            if command:
                command.show_help()
            else:
                show_error(f"Command not found: /{command_name}")
                self.show_help()  # Show general help
        else:
            # Show general help with all commands
            self._show_general_help()

    def _show_general_help(self) -> None:
        """Show general help with all commands organized by category."""
        console.print("\n📚 [bold cyan]GerdsenAI CLI Commands[/bold cyan]\n")

        # Show commands organized by category
        for category in CommandCategory:
            commands = self.registry.list_commands(category)
            if not commands:
                continue

            # Create category header
            category_name = category.value.title()
            console.print(f"[bold yellow]{category_name}:[/bold yellow]")

            # Create table for commands in this category
            table = Table(show_header=False, show_edge=False, padding=(0, 2))
            table.add_column("Command", style="cyan", min_width=20)
            table.add_column("Description", style="white")

            for command in sorted(commands, key=lambda c: c.name):
                # Format command with aliases
                cmd_text = f"/{command.name}"
                if command.aliases:
                    cmd_text += (
                        f" ({', '.join(f'/{alias}' for alias in command.aliases)})"
                    )

                table.add_row(cmd_text, command.description)

            console.print(table)
            console.print()

        # Show usage tip
        console.print(
            "💡 [dim]Use /help <command> for detailed help on a specific command[/dim]"
        )
        console.print(
            "🚀 [dim]Your AI can understand your project and perform intelligent actions![/dim]\n"
        )

    def get_status(self) -> dict[str, Any]:
        """
        Get parser status information.

        Returns:
            Dictionary with parser status
        """
        total_commands = len(self.registry.commands)
        total_aliases = len(self.registry.aliases)

        category_counts = {}
        for category, command_names in self.registry.categories.items():
            category_counts[category.value] = len(command_names)

        return {
            "total_commands": total_commands,
            "total_aliases": total_aliases,
            "category_counts": category_counts,
            "context_keys": list(self.execution_context.keys()),
        }

    def show_status(self) -> None:
        """Display parser status."""
        status = self.get_status()

        console.print("\n⚙️  [bold cyan]Command Parser Status[/bold cyan]\n")
        console.print(f"  Registered Commands: [bold]{status['total_commands']}[/bold]")
        console.print(f"  Command Aliases:     [bold]{status['total_aliases']}[/bold]")
        console.print(
            f"  Context Keys:        [bold]{len(status['context_keys'])}[/bold]"
        )

        if status["category_counts"]:
            console.print("\n  [bold cyan]Commands by Category:[/bold cyan]")
            for category, count in status["category_counts"].items():
                if count > 0:
                    console.print(f"    {category.title()}: [bold]{count}[/bold]")

        console.print()


class CommandAutoDiscovery:
    """Automatic command discovery and registration."""

    def __init__(self, parser: CommandParser):
        """
        Initialize auto-discovery.

        Args:
            parser: Command parser to register discovered commands
        """
        self.parser = parser

    def discover_commands(self, search_paths: list[Path]) -> int:
        """
        Discover and register commands from specified paths.

        Args:
            search_paths: Paths to search for command modules

        Returns:
            Number of commands discovered and registered
        """
        discovered_count = 0

        for search_path in search_paths:
            if not search_path.exists():
                continue

            # Look for Python files that might contain commands
            for py_file in search_path.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue  # Skip private modules

                try:
                    discovered_count += self._discover_from_file(py_file)
                except Exception as e:
                    show_warning(f"Failed to discover commands from {py_file}: {e}")

        return discovered_count

    def _discover_from_file(self, file_path: Path) -> int:
        """
        Discover commands from a Python file.

        Args:
            file_path: Path to Python file

        Returns:
            Number of commands discovered
        """
        # This is a simplified version - in practice you'd use importlib
        # For now, we'll return 0 since this is a more advanced feature
        return 0

    def discover_from_classes(self, classes: list[type[BaseCommand]]) -> int:
        """
        Discover and register commands from command classes.

        Args:
            classes: List of command classes to instantiate and register

        Returns:
            Number of commands registered
        """
        registered_count = 0

        for command_class in classes:
            try:
                if inspect.isclass(command_class) and issubclass(
                    command_class, BaseCommand
                ):
                    # Instantiate and register
                    command_instance = command_class()
                    self.parser.register_command(command_instance)
                    registered_count += 1
            except Exception as e:
                show_warning(
                    f"Failed to register command class {command_class.__name__}: {e}"
                )

        return registered_count
