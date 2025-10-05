"""
Execution mode system for GerdsenAI CLI.

Provides two distinct modes of operation:
- Architect Mode: Plans and proposes changes before execution
- Execute Mode: Takes immediate action without confirmation
"""

import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Available execution modes."""
    ARCHITECT = "architect"  # Plan first, show proposal, wait for approval
    EXECUTE = "execute"      # Take immediate action without confirmation


class ModeManager:
    """Manages execution mode state and transitions."""
    
    MODE_DESCRIPTIONS = {
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
        )
    }
    
    def __init__(self, default_mode: ExecutionMode = ExecutionMode.ARCHITECT):
        """Initialize mode manager.
        
        Args:
            default_mode: Starting execution mode (defaults to ARCHITECT)
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
        """Toggle between modes.
        
        Returns:
            New ExecutionMode after toggle
        """
        if self.current_mode == ExecutionMode.ARCHITECT:
            self.current_mode = ExecutionMode.EXECUTE
        else:
            self.current_mode = ExecutionMode.ARCHITECT
        
        logger.info(f"Mode toggled to: {self.current_mode.value}")
        return self.current_mode
    
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
    
    def get_mode_description(self, mode: Optional[ExecutionMode] = None) -> str:
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
            String suitable for status bar (e.g., "[ARCHITECT]")
        """
        mode_name = self.current_mode.value.upper()
        return f"[{mode_name}]"
    
    def should_require_approval(self) -> bool:
        """Check if current mode requires user approval before actions.
        
        Returns:
            True if approval is required (architect mode)
        """
        return self.current_mode == ExecutionMode.ARCHITECT
