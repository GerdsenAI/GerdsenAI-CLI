"""
Smart Router for Natural Language Intent Handling.

This module routes user input intelligently:
1. Explicit slash commands → CommandParser
2. Natural language → LLM-based intent detection → ActionHandler
3. Low confidence → Clarification questions

This eliminates the need for users to learn slash commands while maintaining
backward compatibility for power users.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..config.settings import Settings
from .agent import ActionIntent, ActionType, IntentParser
from .llm_client import ChatMessage, LLMClient

logger = logging.getLogger(__name__)


class RouteType(Enum):
    """Types of routing decisions."""

    SLASH_COMMAND = "slash_command"  # Explicit command (e.g., /help)
    NATURAL_LANGUAGE = "natural_language"  # Inferred intent from NL
    CLARIFICATION = "clarification"  # Need to ask user
    PASSTHROUGH_CHAT = "passthrough_chat"  # Just chat, no action


@dataclass
class RouteDecision:
    """Represents a routing decision."""

    route_type: RouteType
    command: str | None = None  # For slash commands
    intent: ActionIntent | None = None  # For natural language
    clarification_prompt: str | None = None  # For clarification
    confidence: float = 1.0
    reasoning: str = ""


class SmartRouter:
    """
    Intelligent router that handles both explicit commands and natural language.

    This is the primary entry point for user input, making the CLI more
    intuitive by eliminating the need for slash commands in most cases.
    """

    # Confidence threshold for auto-execution
    HIGH_CONFIDENCE_THRESHOLD = 0.85
    MEDIUM_CONFIDENCE_THRESHOLD = 0.60

    def __init__(
        self,
        llm_client: LLMClient,
        settings: Settings,
        command_parser: Any = None,
    ):
        """
        Initialize the smart router.

        Args:
            llm_client: LLM client for intent detection
            settings: Application settings
            command_parser: Optional command parser for slash commands
        """
        self.llm_client = llm_client
        self.settings = settings
        self.command_parser = command_parser
        self.intent_parser = IntentParser()

        # Track conversation context for better intent detection
        self.conversation_history: list[ChatMessage] = []
        self.recent_files: set[str] = set()

        logger.info("SmartRouter initialized")

    async def route(
        self, user_input: str, project_files: list[str] | None = None
    ) -> RouteDecision:
        """
        Route user input to the appropriate handler.

        Args:
            user_input: Raw user input
            project_files: Optional list of project files for context

        Returns:
            RouteDecision indicating how to handle the input
        """
        user_input = user_input.strip()

        if not user_input:
            return RouteDecision(
                route_type=RouteType.PASSTHROUGH_CHAT,
                reasoning="Empty input",
            )

        # Step 1: Check for explicit slash command
        if user_input.startswith("/"):
            return RouteDecision(
                route_type=RouteType.SLASH_COMMAND,
                command=user_input,
                confidence=1.0,
                reasoning="Explicit slash command detected",
            )

        # Step 2: Check if this looks like pure conversation
        if self._is_pure_chat(user_input):
            return RouteDecision(
                route_type=RouteType.PASSTHROUGH_CHAT,
                confidence=0.9,
                reasoning="Detected conversational query with no file operations",
            )

        # Step 3: Use LLM-based intent detection for action-oriented inputs
        try:
            intent = await self.intent_parser.detect_intent_with_llm(
                self.llm_client, user_input, project_files or []
            )

            # High confidence - execute directly
            if intent.confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
                return RouteDecision(
                    route_type=RouteType.NATURAL_LANGUAGE,
                    intent=intent,
                    confidence=intent.confidence,
                    reasoning=f"High confidence intent: {intent.action_type.value}",
                )

            # Medium confidence - ask for clarification
            elif intent.confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
                clarification = self._build_clarification_prompt(intent, user_input)
                return RouteDecision(
                    route_type=RouteType.CLARIFICATION,
                    intent=intent,
                    clarification_prompt=clarification,
                    confidence=intent.confidence,
                    reasoning=f"Medium confidence ({intent.confidence:.2f}), requesting clarification",
                )

            # Low confidence - treat as chat
            else:
                return RouteDecision(
                    route_type=RouteType.PASSTHROUGH_CHAT,
                    confidence=intent.confidence,
                    reasoning=f"Low confidence ({intent.confidence:.2f}), treating as conversation",
                )

        except Exception as e:
            logger.warning(f"Intent detection failed: {e}, falling back to chat")
            return RouteDecision(
                route_type=RouteType.PASSTHROUGH_CHAT,
                confidence=0.5,
                reasoning=f"Intent detection error: {e}",
            )

    def _is_pure_chat(self, user_input: str) -> bool:
        """
        Determine if input is pure conversation with no action intent.

        Args:
            user_input: User's input text

        Returns:
            True if this looks like conversational chat
        """
        user_lower = user_input.lower()

        # Conversational starters
        chat_indicators = [
            "what is",
            "what's",
            "how does",
            "why does",
            "can you explain",
            "tell me about",
            "explain",
            "what are",
            "how do",
            "should i",
            "would you",
            "do you think",
            "is it",
            "are there",
        ]

        # Action keywords that indicate operations
        action_keywords = [
            "edit",
            "modify",
            "change",
            "update",
            "create",
            "add",
            "delete",
            "remove",
            "fix",
            "refactor",
            "implement",
            "write",
        ]

        # File extensions that suggest file operations
        has_file_extension = bool(
            re.search(r"\.(py|js|ts|java|cpp|md|txt|json|yaml|toml)(\s|$)", user_lower)
        )

        # Check for chat indicators
        starts_with_chat = any(
            user_lower.startswith(indicator) for indicator in chat_indicators
        )

        # Check for action keywords
        has_action = any(keyword in user_lower for keyword in action_keywords)

        # Pure chat if:
        # 1. Starts with conversational phrase AND no file extensions
        # 2. No action keywords AND no file extensions
        return (starts_with_chat and not has_file_extension) or (
            not has_action and not has_file_extension
        )

    def _build_clarification_prompt(
        self, intent: ActionIntent, original_input: str
    ) -> str:
        """
        Build a clarification prompt for medium-confidence intents.

        Args:
            intent: Detected intent with medium confidence
            original_input: Original user input

        Returns:
            Clarification prompt to show user
        """
        action_desc = {
            ActionType.READ_FILE: "read and explain",
            ActionType.EDIT_FILE: "edit",
            ActionType.CREATE_FILE: "create",
            ActionType.DELETE_FILE: "delete",
            ActionType.SEARCH_FILES: "search for",
            ActionType.ANALYZE_PROJECT: "analyze the project structure",
            ActionType.EXECUTE_COMMAND: "execute a command",
        }.get(intent.action_type, "perform an action on")

        files_str = ", ".join(intent.parameters.get("files", ["(no files detected)"]))

        prompt = f"""I understand you want to **{action_desc}** the following:

**Files**: {files_str}

**My understanding**: {intent.reasoning or "No specific reasoning provided"}

**Confidence**: {intent.confidence:.0%}

Is this correct? You can:
- Reply "yes" to proceed
- Correct my understanding (e.g., "no, I meant...")
- Provide more context
"""
        return prompt

    def update_context(self, user_input: str, ai_response: str) -> None:
        """
        Update conversation context for better future routing.

        Args:
            user_input: User's input
            ai_response: AI's response
        """
        # Track conversation history (limit to last 10 exchanges)
        self.conversation_history.append(ChatMessage(role="user", content=user_input))
        self.conversation_history.append(
            ChatMessage(role="assistant", content=ai_response)
        )

        if len(self.conversation_history) > 20:  # 10 exchanges
            self.conversation_history = self.conversation_history[-20:]

        # Extract and track mentioned files
        file_mentions = self._extract_file_mentions(user_input + " " + ai_response)
        self.recent_files.update(file_mentions)

        # Limit recent files tracking
        if len(self.recent_files) > 50:
            # Keep only the most recent mentions (simple FIFO for now)
            self.recent_files = set(list(self.recent_files)[-50:])

    def _extract_file_mentions(self, text: str) -> set[str]:
        """
        Extract file path mentions from text.

        Args:
            text: Text to analyze

        Returns:
            Set of file paths mentioned
        """
        # Simple pattern for common file extensions
        pattern = (
            r"[\w/.-]+\.(?:py|js|ts|java|cpp|h|hpp|md|txt|json|yaml|toml|sh|bash|zsh)"
        )
        matches = re.findall(pattern, text)
        return set(matches)

    def get_recent_files(self) -> list[str]:
        """
        Get list of recently mentioned files.

        Returns:
            List of file paths mentioned in recent conversation
        """
        return list(self.recent_files)

    def clear_context(self) -> None:
        """Clear conversation context and recent files."""
        self.conversation_history.clear()
        self.recent_files.clear()
        logger.info("SmartRouter context cleared")
