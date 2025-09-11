"""
Base command class for GerdsenAI CLI commands.

This module provides the foundation for implementing structured, extensible commands
with proper argument parsing, validation, and help generation.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from rich.console import Console
from rich.table import Table
from rich.text import Text

console = Console()


class CommandCategory(Enum):
    """Categories for organizing commands."""
    SYSTEM = "system"
    MODEL = "model"
    AGENT = "agent"
    FILE = "file"
    CONTEXT = "context"
    SESSION = "session"


@dataclass
class CommandArgument:
    """Represents a command argument definition."""
    name: str
    description: str
    required: bool = False
    arg_type: type = str
    choices: Optional[List[str]] = None
    default: Optional[Any] = None
    
    def validate(self, value: str) -> Any:
        """Validate and convert argument value."""
        if self.choices and value not in self.choices:
            raise ValueError(f"Invalid choice '{value}'. Must be one of: {', '.join(self.choices)}")
        
        try:
            if self.arg_type == bool:
                return value.lower() in {'true', '1', 'yes', 'on'}
            elif self.arg_type == int:
                return int(value)
            elif self.arg_type == float:
                return float(value)
            else:
                return str(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot convert '{value}' to {self.arg_type.__name__}: {e}")


@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    should_exit: bool = False


class BaseCommand(ABC):
    """Abstract base class for all CLI commands."""
    
    def __init__(self):
        """Initialize base command."""
        self._args_cache: Optional[Dict[str, CommandArgument]] = None
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Command name (without leading slash)."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Brief description of the command."""
        pass
    
    @property
    @abstractmethod
    def category(self) -> CommandCategory:
        """Command category for organization."""
        pass
    
    @property
    def aliases(self) -> List[str]:
        """Alternative names for this command."""
        return []
    
    @property
    def arguments(self) -> Dict[str, CommandArgument]:
        """Command arguments definition."""
        if self._args_cache is None:
            self._args_cache = self._define_arguments()
        return self._args_cache
    
    def _define_arguments(self) -> Dict[str, CommandArgument]:
        """Define command arguments. Override in subclasses."""
        return {}
    
    @property
    def usage(self) -> str:
        """Generate usage string for the command."""
        usage_parts = [f"/{self.name}"]
        
        for arg_name, arg_def in self.arguments.items():
            if arg_def.required:
                usage_parts.append(f"<{arg_name}>")
            else:
                default_str = f"={arg_def.default}" if arg_def.default is not None else ""
                usage_parts.append(f"[{arg_name}{default_str}]")
        
        return " ".join(usage_parts)
    
    @property
    def help_text(self) -> str:
        """Generate detailed help text for the command."""
        lines = [
            f"**{self.usage}**",
            "",
            self.description,
        ]
        
        if self.aliases:
            lines.extend([
                "",
                f"**Aliases:** {', '.join(f'/{alias}' for alias in self.aliases)}"
            ])
        
        if self.arguments:
            lines.extend([
                "",
                "**Arguments:**"
            ])
            
            for arg_name, arg_def in self.arguments.items():
                req_str = " (required)" if arg_def.required else ""
                default_str = f" [default: {arg_def.default}]" if arg_def.default is not None else ""
                type_str = f" [{arg_def.arg_type.__name__}]"
                choices_str = f" (choices: {', '.join(arg_def.choices)})" if arg_def.choices else ""
                
                lines.append(f"  `{arg_name}`{type_str}{req_str} - {arg_def.description}{default_str}{choices_str}")
        
        return "\n".join(lines)
    
    def parse_arguments(self, args_text: str) -> Dict[str, Any]:
        """Parse command arguments from text."""
        if not args_text.strip():
            args_text = ""
        
        # Simple argument parsing - split by spaces, handle quoted strings
        raw_args = self._tokenize_arguments(args_text)
        parsed_args = {}
        
        # Get positional arguments first
        positional_args = [arg for arg in self.arguments.values() if arg.required]
        
        # Parse positional arguments
        for i, arg_def in enumerate(positional_args):
            if i < len(raw_args):
                try:
                    parsed_args[arg_def.name] = arg_def.validate(raw_args[i])
                except ValueError as e:
                    raise ValueError(f"Error in argument '{arg_def.name}': {e}")
            else:
                raise ValueError(f"Missing required argument: {arg_def.name}")
        
        # Parse optional arguments (simple key=value format)
        remaining_args = raw_args[len(positional_args):]
        for arg_text in remaining_args:
            if "=" in arg_text:
                key, value = arg_text.split("=", 1)
                if key in self.arguments:
                    try:
                        parsed_args[key] = self.arguments[key].validate(value)
                    except ValueError as e:
                        raise ValueError(f"Error in argument '{key}': {e}")
                else:
                    raise ValueError(f"Unknown argument: {key}")
            else:
                # Treat as boolean flag if it's defined as boolean argument
                if arg_text in self.arguments and self.arguments[arg_text].arg_type == bool:
                    parsed_args[arg_text] = True
                else:
                    raise ValueError(f"Invalid argument format: {arg_text}")
        
        # Add default values for missing optional arguments
        for arg_name, arg_def in self.arguments.items():
            if arg_name not in parsed_args and not arg_def.required:
                parsed_args[arg_name] = arg_def.default
        
        return parsed_args
    
    def _tokenize_arguments(self, args_text: str) -> List[str]:
        """Simple tokenizer that handles quoted strings."""
        if not args_text.strip():
            return []
        
        tokens = []
        current_token = ""
        in_quotes = False
        quote_char = None
        
        i = 0
        while i < len(args_text):
            char = args_text[i]
            
            if not in_quotes:
                if char in ['"', "'"]:
                    in_quotes = True
                    quote_char = char
                elif char.isspace():
                    if current_token:
                        tokens.append(current_token)
                        current_token = ""
                else:
                    current_token += char
            else:
                if char == quote_char:
                    in_quotes = False
                    quote_char = None
                else:
                    current_token += char
            
            i += 1
        
        if current_token:
            tokens.append(current_token)
        
        return tokens
    
    @abstractmethod
    async def execute(self, args: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """
        Execute the command with parsed arguments.
        
        Args:
            args: Parsed command arguments
            context: Execution context (app state, agent, etc.)
            
        Returns:
            CommandResult indicating success/failure and any data
        """
        pass
    
    async def run(self, args_text: str, context: Dict[str, Any]) -> CommandResult:
        """
        Parse arguments and execute the command.
        
        Args:
            args_text: Raw argument string
            context: Execution context
            
        Returns:
            CommandResult from execution
        """
        try:
            parsed_args = self.parse_arguments(args_text)
            return await self.execute(parsed_args, context)
        except ValueError as e:
            return CommandResult(
                success=False,
                message=f"Argument error: {e}\n\nUsage: {self.usage}"
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Command execution failed: {e}"
            )
    
    def show_help(self) -> None:
        """Display help for this command."""
        console.print(f"\n📖 [bold cyan]Help: /{self.name}[/bold cyan]\n")
        console.print(self.help_text)
        console.print()


class AsyncCommandMixin:
    """Mixin for commands that need async execution context."""
    
    async def async_execute(self, args: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Async execution method. Override this instead of execute."""
        return CommandResult(success=True, message="Command completed")
    
    async def execute(self, args: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Execute async command."""
        return await self.async_execute(args, context)


class SimpleCommand(BaseCommand):
    """Simple command implementation for basic commands."""
    
    def __init__(self, name: str, description: str, category: CommandCategory, 
                 handler: callable, aliases: List[str] = None, arguments: Dict[str, CommandArgument] = None):
        """
        Initialize simple command.
        
        Args:
            name: Command name
            description: Command description
            category: Command category
            handler: Function to execute (can be async)
            aliases: Alternative names
            arguments: Command arguments
        """
        super().__init__()
        self._name = name
        self._description = description
        self._category = category
        self._handler = handler
        self._aliases = aliases or []
        self._arguments = arguments or {}
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    @property
    def category(self) -> CommandCategory:
        return self._category
    
    @property
    def aliases(self) -> List[str]:
        return self._aliases
    
    def _define_arguments(self) -> Dict[str, CommandArgument]:
        return self._arguments
    
    async def execute(self, args: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Execute the command handler."""
        try:
            if asyncio.iscoroutinefunction(self._handler):
                result = await self._handler(args, context)
            else:
                result = self._handler(args, context)
            
            if isinstance(result, CommandResult):
                return result
            else:
                return CommandResult(success=True, message=str(result) if result else None)
        except Exception as e:
            return CommandResult(success=False, message=f"Handler error: {e}")
