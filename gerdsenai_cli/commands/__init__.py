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
from .intelligence import IntelligenceCommand
from .memory import MemoryCommand
from .model import (
    ListModelsCommand,
    ModelInfoCommand,
    ModelStatsCommand,
    SwitchModelCommand,
)
from .parser import CommandParser
from .planning import PlanCommand
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
from .vision_commands import (
    ImageCommand,
    OCRCommand,
    VisionStatusCommand,
)
from .audio_commands import (
    TranscribeCommand,
    SpeakCommand,
    AudioStatusCommand,
)
from .clarify_commands import ClarifyCommand
from .complexity_commands import ComplexityCommand
from .undo_commands import UndoCommand
from .suggest_commands import SuggestCommand

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
    "PlanCommand",
    "MemoryCommand",
    "IntelligenceCommand",
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
