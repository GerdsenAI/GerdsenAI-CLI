"""
Tests for execution mode system.
"""

import pytest

from gerdsenai_cli.core.modes import (
    ExecutionMode,
    ModeManager,
)


class TestExecutionMode:
    """Test ExecutionMode enum."""
    
    def test_mode_values(self):
        """Test mode enum values."""
        assert ExecutionMode.CHAT.value == "chat"
        assert ExecutionMode.ARCHITECT.value == "architect"
        assert ExecutionMode.EXECUTE.value == "execute"
        assert ExecutionMode.LLVL.value == "llvl"


class TestModeManager:
    """Test mode manager functionality."""
    
    def test_initialization_default(self):
        """Test manager initializes with default mode (CHAT)."""
        manager = ModeManager()
        
        assert manager.get_mode() == ExecutionMode.CHAT
    
    def test_initialization_custom(self):
        """Test manager initializes with custom mode."""
        manager = ModeManager(default_mode=ExecutionMode.EXECUTE)
        
        assert manager.get_mode() == ExecutionMode.EXECUTE
    
    def test_set_mode(self):
        """Test setting execution mode."""
        manager = ModeManager()
        
        manager.set_mode(ExecutionMode.LLVL)
        
        assert manager.get_mode() == ExecutionMode.LLVL
    
    def test_toggle_mode_cycles_correctly(self):
        """Test that toggle cycles through all modes in order."""
        manager = ModeManager(default_mode=ExecutionMode.CHAT)
        
        # CHAT -> ARCHITECT
        mode = manager.toggle_mode()
        assert mode == ExecutionMode.ARCHITECT
        
        # ARCHITECT -> EXECUTE
        mode = manager.toggle_mode()
        assert mode == ExecutionMode.EXECUTE
        
        # EXECUTE -> LLVL
        mode = manager.toggle_mode()
        assert mode == ExecutionMode.LLVL
        
        # LLVL -> CHAT (wraps around)
        mode = manager.toggle_mode()
        assert mode == ExecutionMode.CHAT
    
    def test_is_chat_mode(self):
        """Test chat mode check."""
        manager = ModeManager(default_mode=ExecutionMode.CHAT)
        
        assert manager.is_chat_mode() is True
        assert manager.is_architect_mode() is False
        assert manager.is_execute_mode() is False
        assert manager.is_llvl_mode() is False
    
    def test_is_architect_mode(self):
        """Test architect mode check."""
        manager = ModeManager(default_mode=ExecutionMode.ARCHITECT)
        
        assert manager.is_architect_mode() is True
        assert manager.is_chat_mode() is False
        assert manager.is_execute_mode() is False
        assert manager.is_llvl_mode() is False
    
    def test_is_execute_mode(self):
        """Test execute mode check."""
        manager = ModeManager(default_mode=ExecutionMode.EXECUTE)
        
        assert manager.is_execute_mode() is True
        assert manager.is_chat_mode() is False
        assert manager.is_architect_mode() is False
        assert manager.is_llvl_mode() is False
    
    def test_is_llvl_mode(self):
        """Test LLVL mode check."""
        manager = ModeManager(default_mode=ExecutionMode.LLVL)
        
        assert manager.is_llvl_mode() is True
        assert manager.is_chat_mode() is False
        assert manager.is_architect_mode() is False
        assert manager.is_execute_mode() is False
    
    def test_allows_actions_chat_mode(self):
        """Test that CHAT mode blocks actions."""
        manager = ModeManager(default_mode=ExecutionMode.CHAT)
        
        assert manager.allows_actions() is False
    
    def test_allows_actions_other_modes(self):
        """Test that non-CHAT modes allow actions."""
        manager = ModeManager(default_mode=ExecutionMode.ARCHITECT)
        assert manager.allows_actions() is True
        
        manager.set_mode(ExecutionMode.EXECUTE)
        assert manager.allows_actions() is True
        
        manager.set_mode(ExecutionMode.LLVL)
        assert manager.allows_actions() is True
    
    def test_get_mode_description_current(self):
        """Test getting description for current mode."""
        manager = ModeManager(default_mode=ExecutionMode.CHAT)
        
        description = manager.get_mode_description()
        
        assert "Chat Mode" in description
        assert "conversation" in description.lower()
    
    def test_get_mode_description_llvl(self):
        """Test getting description for LLVL mode."""
        manager = ModeManager()
        
        description = manager.get_mode_description(ExecutionMode.LLVL)
        
        assert "LLVL Mode" in description
        assert "Livin' La Vida Loca" in description
        assert "maximum speed" in description.lower()
        assert "WARNING" in description
    
    def test_format_status_line_all_modes(self):
        """Test status line formatting for all modes."""
        manager = ModeManager(default_mode=ExecutionMode.CHAT)
        assert manager.format_status_line() == "[CHAT]"
        
        manager.set_mode(ExecutionMode.ARCHITECT)
        assert manager.format_status_line() == "[ARCHITECT]"
        
        manager.set_mode(ExecutionMode.EXECUTE)
        assert manager.format_status_line() == "[EXECUTE]"
        
        manager.set_mode(ExecutionMode.LLVL)
        assert manager.format_status_line() == "[LLVL]"
    
    def test_should_require_approval(self):
        """Test approval requirement logic."""
        manager = ModeManager()
        
        # CHAT mode doesn't allow actions at all
        assert manager.should_require_approval() is False
        
        # ARCHITECT requires approval
        manager.set_mode(ExecutionMode.ARCHITECT)
        assert manager.should_require_approval() is True
        
        # EXECUTE doesn't require approval
        manager.set_mode(ExecutionMode.EXECUTE)
        assert manager.should_require_approval() is False
        
        # LLVL doesn't require approval
        manager.set_mode(ExecutionMode.LLVL)
        assert manager.should_require_approval() is False
    
    def test_should_block_actions(self):
        """Test action blocking logic."""
        manager = ModeManager(default_mode=ExecutionMode.CHAT)
        
        # CHAT mode blocks actions
        assert manager.should_block_actions() is True
        
        # Other modes don't block
        manager.set_mode(ExecutionMode.ARCHITECT)
        assert manager.should_block_actions() is False
        
        manager.set_mode(ExecutionMode.EXECUTE)
        assert manager.should_block_actions() is False
        
        manager.set_mode(ExecutionMode.LLVL)
        assert manager.should_block_actions() is False
    
    def test_get_action_suggestion_message(self):
        """Test suggestion message for CHAT mode."""
        manager = ModeManager(default_mode=ExecutionMode.CHAT)
        
        message = manager.get_action_suggestion_message()
        
        assert "Chat Mode" in message
        assert "Shift+Tab" in message
        assert "architect" in message.lower()
        assert "execute" in message.lower()
        assert "llvl" in message.lower()
