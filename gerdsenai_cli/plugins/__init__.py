"""
Plugin System for GerdsenAI CLI.

Extensible plugin architecture for multimodal capabilities,
simulations, tools, and agents.

Design Principles:
- Protocol-based: Plugins implement protocols, not inherit from base classes
- Auto-discovery: Plugins are automatically discovered and registered
- Type-safe: Full type hints for all plugin interfaces
- Async-native: All operations support async/await
- Streaming-first: Real-time processing support

Plugin Categories:
- vision: Image understanding, OCR, object detection
- audio: Speech-to-text, text-to-speech, audio generation
- video: Video analysis and understanding
- simulation: Isaac Sim, Unreal, Unity bridges
- tools: Function calling and tool execution
- agents: Multi-agent orchestration
"""

from .base import (
    ContentPart,
    ContentType,
    MultimodalMessage,
    Plugin,
    PluginCategory,
    PluginMetadata,
)
from .registry import PluginRegistry, plugin_registry

__all__ = [
    "Plugin",
    "PluginCategory",
    "PluginMetadata",
    "ContentType",
    "ContentPart",
    "MultimodalMessage",
    "PluginRegistry",
    "plugin_registry",
]
