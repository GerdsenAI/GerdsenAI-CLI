"""
Command implementations module for GerdsenAI CLI.

This module contains all slash command implementations and the command parser.
"""

from .base import BaseCommand
from .parser import CommandParser
from .system import HelpCommand, ExitCommand, StatusCommand, ConfigCommand, DebugCommand
from .model import ListModelsCommand, SwitchModelCommand, ModelInfoCommand, ModelStatsCommand
from .agent import AgentStatusCommand, ConversationCommand, RefreshContextCommand, ClearSessionCommand, AgentConfigCommand
from .files import ListFilesCommand, ReadFileCommand, EditFileCommand, CreateFileCommand, SearchFilesCommand, SessionCommand

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
