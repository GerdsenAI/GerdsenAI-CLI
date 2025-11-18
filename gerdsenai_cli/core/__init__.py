"""
Core business logic module for GerdsenAI CLI.

This module contains the main business logic including LLM client, agent logic,
context management, file editing, and terminal integration.

Import specific modules directly (e.g., from gerdsenai_cli.core.agent import Agent).
"""

from .llm_client import LLMClient

__all__ = ["LLMClient"]
