"""
Core business logic module for GerdsenAI CLI.

This module contains the main business logic including LLM client, agent logic,
context management, file editing, and terminal integration.
"""

from .llm_client import LLMClient

__all__ = ["LLMClient"]

# TODO: Add imports as we implement additional modules:
# from .agent import Agent
# from .context_manager import ProjectContext  
# from .file_editor import FileEditor
# from .terminal import TerminalExecutor
