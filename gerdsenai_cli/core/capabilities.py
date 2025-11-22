"""
AI model capability detection system.

Detects and tracks what features the current AI model supports:
- Thinking/reasoning display
- Vision/image understanding
- Tool/function calling
- Streaming responses
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ModelCapabilities:
    """Represents detected capabilities of an AI model."""

    supports_thinking: bool = False
    supports_vision: bool = False
    supports_tools: bool = False
    supports_streaming: bool = False
    model_name: str | None = None
    detected_at: str | None = None


class CapabilityDetector:
    """Detects AI model capabilities through probing and metadata."""

    # Known models with thinking support
    THINKING_MODELS = [
        "claude-3",
        "claude-2",
        "gpt-4",
        "o1-preview",
        "o1-mini",
        "deepseek",
        "qwen",
    ]

    # Known models with vision support
    VISION_MODELS = [
        "claude-3",
        "gpt-4-vision",
        "gpt-4o",
        "gemini-pro-vision",
        "llava",
        "bakllava",
    ]

    # Known models with tool calling
    TOOL_MODELS = [
        "claude-3",
        "gpt-4",
        "gpt-3.5-turbo",
        "gemini-pro",
        "mistral",
    ]

    @staticmethod
    def detect_from_model_name(model_name: str) -> ModelCapabilities:
        """Detect capabilities based on model name.

        Args:
            model_name: Name or identifier of the model

        Returns:
            ModelCapabilities with detected features
        """
        if not model_name:
            return ModelCapabilities()

        model_lower = model_name.lower()

        # Check for thinking support
        supports_thinking = any(
            known in model_lower for known in CapabilityDetector.THINKING_MODELS
        )

        # Check for vision support
        supports_vision = any(
            known in model_lower for known in CapabilityDetector.VISION_MODELS
        )

        # Check for tool calling
        supports_tools = any(
            known in model_lower for known in CapabilityDetector.TOOL_MODELS
        )

        # Most modern models support streaming
        supports_streaming = True

        capabilities = ModelCapabilities(
            supports_thinking=supports_thinking,
            supports_vision=supports_vision,
            supports_tools=supports_tools,
            supports_streaming=supports_streaming,
            model_name=model_name,
        )

        logger.info(
            f"Detected capabilities for {model_name}: "
            f"thinking={supports_thinking}, vision={supports_vision}, "
            f"tools={supports_tools}, streaming={supports_streaming}"
        )

        return capabilities

    @staticmethod
    async def probe_capabilities(agent) -> ModelCapabilities:
        """Probe AI agent to detect capabilities dynamically.

        Args:
            agent: The AI agent instance

        Returns:
            ModelCapabilities with detected features
        """
        capabilities = ModelCapabilities()

        try:
            # Get model name from agent
            model_name = getattr(agent, "model_name", None) or getattr(
                agent, "model", None
            )

            if not model_name and hasattr(agent, "settings"):
                model_name = getattr(agent.settings, "current_model", None) or getattr(
                    agent.settings, "model", None
                )

            if model_name:
                capabilities = CapabilityDetector.detect_from_model_name(model_name)

            # Try to detect from agent metadata if available
            if hasattr(agent, "get_capabilities"):
                agent_caps = await agent.get_capabilities()
                capabilities.supports_thinking = agent_caps.get("thinking", False)
                capabilities.supports_vision = agent_caps.get("vision", False)
                capabilities.supports_tools = agent_caps.get("tools", False)
                capabilities.supports_streaming = agent_caps.get("streaming", True)

            logger.info(f"Probed capabilities: {capabilities}")

        except Exception as e:
            logger.warning(f"Failed to probe capabilities: {e}")

        return capabilities
