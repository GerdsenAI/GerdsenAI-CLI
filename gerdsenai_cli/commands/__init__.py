"""
Command implementations module for GerdsenAI CLI.

This module contains all slash command implementations and the command parser.
"""

from .agent import (
    AgentConfigCommand,
    AgentStatusCommand,
    ClearSessionCommand,
    ConversationCommand,
    RefreshContextCommand,
)
from .base import BaseCommand
from .files import (
    CreateFileCommand,
    EditFileCommand,
    ListFilesCommand,
    ReadFileCommand,
    SearchFilesCommand,
    SessionCommand,
)
from .model import (
    ListModelsCommand,
    ModelInfoCommand,
    ModelStatsCommand,
    SwitchModelCommand,
)
from .parser import CommandParser
from .system import ConfigCommand, DebugCommand, ExitCommand, HelpCommand, StatusCommand

__all__ = [
    "BaseCommand",
    "CommandParser",
    # System commands
    "HelpCommand",
    "ExitCommand",
    "StatusCommand",
    "ConfigCommand",
    "DebugCommand",
    # Model commands
    "ListModelsCommand",
    "SwitchModelCommand",
    "ModelInfoCommand",
    "ModelStatsCommand",
    # Agent commands
    "AgentStatusCommand",
    "ConversationCommand",
    "RefreshContextCommand",
    "ClearSessionCommand",
    "AgentConfigCommand",
    # File commands
    "ListFilesCommand",
    "ReadFileCommand",
    "EditFileCommand",
    "CreateFileCommand",
    "SearchFilesCommand",
    "SessionCommand",
]
