"""
Command implementations module for GerdsenAI CLI.

This module contains all slash command implementations and the command parser.
"""

from .agent import (
    AgentConfigCommand,
    AgentStatusCommand,
    ChatCommand,
    RefreshContextCommand,
    ResetCommand,
)
from .base import BaseCommand
from .files import (
    CreateFileCommand,
    EditFileCommand,
    FilesCommand,
    ReadCommand,
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
from .system import (
    AboutCommand,
    ConfigCommand,
    CopyCommand,
    DebugCommand,
    ExitCommand,
    HelpCommand,
    InitCommand,
    SetupCommand,
    StatusCommand,
    ToolsCommand,
)

__all__ = [
    "BaseCommand",
    "CommandParser",
    # System commands
    "HelpCommand",
    "ExitCommand",
    "StatusCommand",
    "ConfigCommand",
    "DebugCommand",
    "AboutCommand",
    "CopyCommand",
    "InitCommand",
    "SetupCommand",
    "ToolsCommand",
    # Model commands
    "ListModelsCommand",
    "SwitchModelCommand",
    "ModelInfoCommand",
    "ModelStatsCommand",
    # Agent commands
    "AgentStatusCommand",
    "ChatCommand",
    "RefreshContextCommand",
    "ResetCommand",
    "AgentConfigCommand",
    # File commands
    "FilesCommand",
    "ReadCommand",
    "EditFileCommand",
    "CreateFileCommand",
    "SearchFilesCommand",
    "SessionCommand",
]
