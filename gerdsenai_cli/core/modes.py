"""
Execution mode system for GerdsenAI CLI.

Provides four distinct modes of operation:
- Chat Mode: Pure conversation, suggests mode switches when action is needed
- Architect Mode: Plans and proposes changes before execution
- Execute Mode: Takes immediate action without confirmation
- LLVL Mode: Livin' La Vida Loca - Maximum speed, minimal safety, YOLO-style
"""

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Available execution modes."""

    CHAT = "chat"  # Conversational only, no actions without explicit mode switch
    ARCHITECT = "architect"  # Plan first, show proposal, wait for approval
    EXECUTE = "execute"  # Take immediate action without confirmation
    LLVL = "llvl"  # Livin' La Vida Loca - Maximum speed, skip all safety checks


class ModeManager:
    """Manages execution mode state and transitions."""

    MODE_DESCRIPTIONS = {
        ExecutionMode.CHAT: (
            "Chat Mode - Pure conversation and exploration.\n"
            "The AI will:\n"
            "  • Answer questions and explain concepts\n"
            "  • Discuss ideas and provide guidance\n"
            "  • Review code and offer suggestions\n"
            "  • Suggest switching modes if action is needed\n"
            "\n"
            "Best for: Learning, planning, Q&A, code review"
        ),
        ExecutionMode.ARCHITECT: (
            "Architect Mode - Plans and proposes changes before execution.\n"
            "The AI will:\n"
            "  • Analyze your request and break it into steps\n"
            "  • Show you a detailed plan with estimates\n"
            "  • Wait for your approval before making changes\n"
            "  • Explain each step as it executes\n"
            "\n"
            "Best for: Complex tasks, refactoring, learning"
        ),
        ExecutionMode.EXECUTE: (
            "Execute Mode - Takes immediate action without confirmation.\n"
            "The AI will:\n"
            "  • Perform requested changes immediately\n"
            "  • Skip plan approval steps\n"
            "  • Make file modifications directly\n"
            "  • Show results when complete\n"
            "\n"
            "Best for: Simple tasks, quick fixes, trusted operations"
        ),
        ExecutionMode.LLVL: (
            "LLVL Mode - Livin' La Vida Loca! Maximum speed, minimal safety.\n"
            "The AI will:\n"
            "  • Execute commands without ANY confirmation\n"
            "  • Skip all safety checks and validation\n"
            "  • Make rapid changes across multiple files\n"
            "  • Assume you know what you're doing\n"
            "\n"
            "WARNING: Use only if you:\n"
            "  • Have version control enabled\n"
            "  • Trust the AI completely\n"
            "  • Want maximum speed over safety\n"
            "  • Are feeling adventurous\n"
            "\n"
            "Best for: Power users, experimentation, rapid prototyping"
        ),
    }

    # Cycle order for Shift+Tab
    MODE_CYCLE = [
        ExecutionMode.CHAT,
        ExecutionMode.ARCHITECT,
        ExecutionMode.EXECUTE,
        ExecutionMode.LLVL,
    ]

    def __init__(self, default_mode: ExecutionMode = ExecutionMode.CHAT):
        """Initialize mode manager.

        Args:
            default_mode: Starting execution mode (defaults to CHAT for safety)
        """
        self.current_mode = default_mode
        logger.info(f"ModeManager initialized with {default_mode.value} mode")

    def get_mode(self) -> ExecutionMode:
        """Get current execution mode.

        Returns:
            Current ExecutionMode
        """
        return self.current_mode

    def set_mode(self, mode: ExecutionMode) -> None:
        """Set execution mode.

        Args:
            mode: ExecutionMode to activate
        """
        old_mode = self.current_mode
        self.current_mode = mode
        logger.info(f"Mode changed: {old_mode.value} -> {mode.value}")

    def toggle_mode(self) -> ExecutionMode:
        """Cycle to next mode in sequence.

        Cycles through: CHAT -> ARCHITECT -> EXECUTE -> LLVL -> CHAT

        Returns:
            New ExecutionMode after toggle
        """
        current_index = self.MODE_CYCLE.index(self.current_mode)
        next_index = (current_index + 1) % len(self.MODE_CYCLE)
        self.current_mode = self.MODE_CYCLE[next_index]

        logger.info(f"Mode cycled to: {self.current_mode.value}")
        return self.current_mode

    def is_chat_mode(self) -> bool:
        """Check if currently in chat mode.

        Returns:
            True if in chat mode
        """
        return self.current_mode == ExecutionMode.CHAT

    def is_architect_mode(self) -> bool:
        """Check if currently in architect mode.

        Returns:
            True if in architect mode
        """
        return self.current_mode == ExecutionMode.ARCHITECT

    def is_execute_mode(self) -> bool:
        """Check if currently in execute mode.

        Returns:
            True if in execute mode
        """
        return self.current_mode == ExecutionMode.EXECUTE

    def is_llvl_mode(self) -> bool:
        """Check if currently in LLVL mode.

        Returns:
            True if in LLVL mode
        """
        return self.current_mode == ExecutionMode.LLVL

    def allows_actions(self) -> bool:
        """Check if current mode allows file/system actions.

        Returns:
            True if actions are allowed (all modes except CHAT)
        """
        return self.current_mode != ExecutionMode.CHAT

    def get_mode_description(self, mode: ExecutionMode | None = None) -> str:
        """Get description for a mode.

        Args:
            mode: ExecutionMode to describe (defaults to current mode)

        Returns:
            Mode description string
        """
        if mode is None:
            mode = self.current_mode
        return self.MODE_DESCRIPTIONS.get(mode, "Unknown mode")

    def format_status_line(self) -> str:
        """Format current mode for status display.

        Returns:
            String suitable for status bar (e.g., "[CHAT]", "[LLVL]")
        """
        mode_name = self.current_mode.value.upper()
        return f"[{mode_name}]"

    def should_require_approval(self) -> bool:
        """Check if current mode requires user approval before actions.

        Returns:
            True if approval is required (architect mode only)
        """
        return self.current_mode == ExecutionMode.ARCHITECT

    def should_block_actions(self) -> bool:
        """Check if current mode should block all actions.

        Returns:
            True if actions should be blocked (chat mode only)
        """
        return self.current_mode == ExecutionMode.CHAT

    def get_action_suggestion_message(self) -> str:
        """Get message to suggest mode switch when action is requested in CHAT mode.

        Returns:
            Suggestion message for user
        """
        return (
            "I noticed you're asking me to make changes, but we're in Chat Mode.\n\n"
            "Chat Mode is for conversations only. To take action, please switch modes:\n"
            "  • Press Shift+Tab to cycle to Architect Mode (plan first)\n"
            "  • Use '/mode architect' for detailed planning\n"
            "  • Use '/mode execute' for immediate execution\n"
            "  • Use '/mode llvl' if you're Livin' La Vida Loca\n\n"
            "Would you like me to explain what I could do in a different mode?"
        )
