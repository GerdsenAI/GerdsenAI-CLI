"""
Base Plugin Protocol and Multimodal Message Format.

Defines the core interfaces that all plugins must implement.
Uses Protocol for maximum flexibility (duck typing with type safety).
"""

from abc import abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

# =============================================================================
# ENUMS
# =============================================================================


class PluginCategory(Enum):
    """Plugin category for organization and discovery."""

    VISION = "vision"
    AUDIO = "audio"
    VIDEO = "video"
    SIMULATION = "simulation"
    TOOL = "tool"
    AGENT = "agent"
    INTEGRATION = "integration"


class ContentType(Enum):
    """Type of content in multimodal messages."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"
    SIMULATION_STATE = "simulation_state"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"


# =============================================================================
# MULTIMODAL MESSAGE FORMAT
# =============================================================================


@dataclass
class ContentPart:
    """
    Single piece of content (text, image, audio, video, etc.).

    This is the atomic unit of multimodal communication.
    """

    type: ContentType
    data: Any  # Actual content (str, bytes, Path, dict, etc.)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate content part."""
        if self.type == ContentType.TEXT and not isinstance(self.data, str):
            raise ValueError(f"TEXT content must be str, got {type(self.data)}")
        elif self.type == ContentType.IMAGE:
            if not isinstance(self.data, (str, Path, bytes)):
                raise ValueError(
                    f"IMAGE content must be str|Path|bytes, got {type(self.data)}"
                )
        elif self.type == ContentType.AUDIO:
            if not isinstance(self.data, (str, Path, bytes)):
                raise ValueError(
                    f"AUDIO content must be str|Path|bytes, got {type(self.data)}"
                )

    @classmethod
    def text(cls, content: str, **metadata) -> "ContentPart":
        """Create text content part."""
        return cls(type=ContentType.TEXT, data=content, metadata=metadata)

    @classmethod
    def image(cls, image: str | Path | bytes, **metadata) -> "ContentPart":
        """Create image content part."""
        return cls(type=ContentType.IMAGE, data=image, metadata=metadata)

    @classmethod
    def audio(cls, audio: str | Path | bytes, **metadata) -> "ContentPart":
        """Create audio content part."""
        return cls(type=ContentType.AUDIO, data=audio, metadata=metadata)

    @classmethod
    def video(cls, video: str | Path, **metadata) -> "ContentPart":
        """Create video content part."""
        return cls(type=ContentType.VIDEO, data=video, metadata=metadata)

    @classmethod
    def file(cls, file_path: str | Path, **metadata) -> "ContentPart":
        """Create file content part."""
        return cls(type=ContentType.FILE, data=Path(file_path), metadata=metadata)


@dataclass
class MultimodalMessage:
    """
    Universal message format for all modalities.

    Supports text, images, audio, video, files, and more in a single message.
    This is how frontier AI companies (OpenAI, Anthropic, Google) structure messages.
    """

    role: str  # "user" | "assistant" | "system" | "tool"
    content: list[ContentPart]  # List of content parts (multimodal)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate message."""
        if self.role not in ("user", "assistant", "system", "tool"):
            raise ValueError(f"Invalid role: {self.role}")
        if not self.content:
            raise ValueError("Message must have at least one content part")

    @classmethod
    def from_text(cls, role: str, text: str, **metadata) -> "MultimodalMessage":
        """Create message from simple text."""
        return cls(role=role, content=[ContentPart.text(text)], metadata=metadata)

    @classmethod
    def from_image(
        cls, role: str, image: str | Path | bytes, prompt: str | None = None, **metadata
    ) -> "MultimodalMessage":
        """Create message with image (optionally with text prompt)."""
        content_parts = []
        if prompt:
            content_parts.append(ContentPart.text(prompt))
        content_parts.append(ContentPart.image(image))

        return cls(role=role, content=content_parts, metadata=metadata)

    def get_text_content(self) -> str:
        """Extract all text content from message."""
        text_parts = [
            part.data for part in self.content if part.type == ContentType.TEXT
        ]
        return "\n".join(text_parts)

    def get_images(self) -> list[str | Path | bytes]:
        """Extract all images from message."""
        return [part.data for part in self.content if part.type == ContentType.IMAGE]

    def has_type(self, content_type: ContentType) -> bool:
        """Check if message contains content of given type."""
        return any(part.type == content_type for part in self.content)


# =============================================================================
# PLUGIN METADATA
# =============================================================================


@dataclass
class PluginMetadata:
    """Metadata about a plugin."""

    name: str
    version: str
    category: PluginCategory
    description: str
    author: str | None = None
    dependencies: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    configuration: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate metadata."""
        if not self.name:
            raise ValueError("Plugin name cannot be empty")
        if not self.version:
            raise ValueError("Plugin version cannot be empty")


# =============================================================================
# PLUGIN PROTOCOL
# =============================================================================


@runtime_checkable
class Plugin(Protocol):
    """
    Base protocol for all plugins.

    All plugins must implement this interface.
    Uses Protocol for duck typing with type safety.
    """

    metadata: PluginMetadata

    async def initialize(self) -> bool:
        """
        Initialize plugin resources.

        Returns:
            True if initialization successful, False otherwise
        """
        ...

    async def shutdown(self) -> None:
        """
        Cleanup plugin resources.

        Called when plugin is being unloaded or application is shutting down.
        """
        ...

    async def health_check(self) -> dict[str, Any]:
        """
        Check plugin health status.

        Returns:
            Dictionary with health information:
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "message": "...",
                "details": {...}
            }
        """
        ...


# =============================================================================
# STREAMING PROCESSOR PROTOCOL
# =============================================================================


@runtime_checkable
class StreamingProcessor(Protocol):
    """
    Protocol for streaming processors.

    Plugins that process data in real-time should implement this.
    """

    async def process_stream(
        self, input_stream: AsyncGenerator[ContentPart, None]
    ) -> AsyncGenerator[ContentPart, None]:
        """
        Process input stream and yield output stream.

        Args:
            input_stream: Async generator of input content parts

        Yields:
            Output content parts
        """
        ...


# =============================================================================
# VISION PLUGIN PROTOCOL
# =============================================================================


@runtime_checkable
class VisionPlugin(Plugin, Protocol):
    """
    Protocol for vision plugins.

    Plugins that process images should implement this.
    """

    @abstractmethod
    async def understand_image(
        self, image: str | Path | bytes, prompt: str | None = None
    ) -> str:
        """
        Understand image content and optionally answer a question.

        Args:
            image: Image file path, URL, or raw bytes
            prompt: Optional question about the image

        Returns:
            Description or answer about the image
        """
        ...

    async def ocr(
        self, image: str | Path | bytes, languages: list[str] = None
    ) -> str:
        """
        Extract text from image using OCR.

        Args:
            image: Image file path, URL, or raw bytes
            languages: List of language codes (e.g., ["en", "es"])

        Returns:
            Extracted text
        """
        ...


# =============================================================================
# AUDIO PLUGIN PROTOCOL
# =============================================================================


@runtime_checkable
class AudioPlugin(Plugin, Protocol):
    """
    Protocol for audio plugins.

    Plugins that process audio should implement this.
    """

    @abstractmethod
    async def transcribe(
        self, audio: str | Path | bytes, language: str | None = None
    ) -> str:
        """
        Transcribe audio to text.

        Args:
            audio: Audio file path or raw bytes
            language: Optional language code (e.g., "en")

        Returns:
            Transcribed text
        """
        ...

    async def generate_speech(
        self, text: str, voice: str | None = None, **kwargs
    ) -> bytes:
        """
        Generate speech from text.

        Args:
            text: Text to convert to speech
            voice: Optional voice identifier
            **kwargs: Additional parameters (speed, emotion, etc.)

        Returns:
            Audio bytes (WAV format)
        """
        ...


# =============================================================================
# VIDEO PLUGIN PROTOCOL
# =============================================================================


@runtime_checkable
class VideoPlugin(Plugin, Protocol):
    """
    Protocol for video plugins.

    Plugins that process video should implement this.
    """

    @abstractmethod
    async def understand_video(
        self, video: str | Path, prompt: str | None = None, sample_fps: float = 1.0
    ) -> str:
        """
        Understand video content.

        Args:
            video: Video file path
            prompt: Optional question about the video
            sample_fps: Frames per second to sample

        Returns:
            Description or analysis of video content
        """
        ...


# =============================================================================
# TOOL PROTOCOL
# =============================================================================


@runtime_checkable
class Tool(Protocol):
    """
    Protocol for tools (function calling).

    Tools are functions that LLMs can call.
    """

    name: str
    description: str

    async def execute(self, **kwargs) -> Any:
        """
        Execute tool with given arguments.

        Args:
            **kwargs: Tool-specific arguments

        Returns:
            Tool execution result
        """
        ...

    def get_schema(self) -> dict:
        """
        Get tool schema for LLM.

        Returns:
            JSON schema describing tool parameters
        """
        ...


# =============================================================================
# AGENT PROTOCOL
# =============================================================================


@runtime_checkable
class Agent(Protocol):
    """
    Protocol for agents in multi-agent systems.

    Agents are autonomous entities that can perform tasks.
    """

    name: str
    role: str  # "coordinator" | "researcher" | "coder" | "vision_expert" | etc.
    capabilities: list[str]

    async def process_task(self, task: str, context: dict[str, Any]) -> str:
        """
        Process task and return result.

        Args:
            task: Task description
            context: Additional context for task

        Returns:
            Task result
        """
        ...

    async def communicate(self, message: str, target_agent: str | None = None) -> None:
        """
        Communicate with other agents.

        Args:
            message: Message to send
            target_agent: Optional specific agent to send to (broadcast if None)
        """
        ...


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "PluginCategory",
    "ContentType",
    "ContentPart",
    "MultimodalMessage",
    "PluginMetadata",
    "Plugin",
    "StreamingProcessor",
    "VisionPlugin",
    "AudioPlugin",
    "VideoPlugin",
    "Tool",
    "Agent",
]
