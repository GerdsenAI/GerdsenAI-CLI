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
from .audio_commands import (
    AudioStatusCommand,
    SpeakCommand,
    TranscribeCommand,
)
from .base import BaseCommand
from .clarify_commands import ClarifyCommand
from .complexity_commands import ComplexityCommand
from .discover import DiscoverCommand
from .files import (
    CreateFileCommand,
    EditFileCommand,
    FilesCommand,
    ReadCommand,
    SearchFilesCommand,
    SessionCommand,
)
from .memory import MemoryCommand
from .model import (
    ListModelsCommand,
    ModelInfoCommand,
    ModelStatsCommand,
    SwitchModelCommand,
)
from .parser import CommandParser
from .planning import PlanCommand
from .suggest_commands import SuggestCommand
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
from .undo_commands import UndoCommand
from .vision_commands import (
    ImageCommand,
    OCRCommand,
    VisionStatusCommand,
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
    "DiscoverCommand",
    # Agent commands
    "AgentStatusCommand",
    "ChatCommand",
    "RefreshContextCommand",
    "ResetCommand",
    "AgentConfigCommand",
    "PlanCommand",
    "MemoryCommand",
    "ClarifyCommand",
    "ComplexityCommand",
    "UndoCommand",
    "SuggestCommand",
    # File commands
    "FilesCommand",
    "ReadCommand",
    "EditFileCommand",
    "CreateFileCommand",
    "SearchFilesCommand",
    "SessionCommand",
    # Vision commands
    "ImageCommand",
    "OCRCommand",
    "VisionStatusCommand",
    # Audio commands
    "TranscribeCommand",
    "SpeakCommand",
    "AudioStatusCommand",
]
