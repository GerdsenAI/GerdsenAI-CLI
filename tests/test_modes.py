"""
Tests for execution mode system.
"""

from gerdsenai_cli.core.modes import (
    ExecutionMode,
    ModeManager,
)


class TestExecutionMode:
    """Test ExecutionMode enum."""
    
    def test_mode_values(self):
        """Test mode enum values."""
        assert ExecutionMode.ARCHITECT.value == "architect"
        assert ExecutionMode.EXECUTE.value == "execute"


class TestModeManager:
    """Test mode manager functionality."""
    
    def test_initialization_default(self):
        """Test manager initializes with default mode."""
        manager = ModeManager()
        
        assert manager.get_mode() == ExecutionMode.ARCHITECT
    
    def test_initialization_custom(self):
        """Test manager initializes with custom mode."""
        manager = ModeManager(default_mode=ExecutionMode.EXECUTE)
        
        assert manager.get_mode() == ExecutionMode.EXECUTE
    
    def test_set_mode(self):
        """Test setting execution mode."""
        manager = ModeManager()
        
        manager.set_mode(ExecutionMode.EXECUTE)
        
        assert manager.get_mode() == ExecutionMode.EXECUTE
    
    def test_toggle_mode_from_architect(self):
        """Test toggling from architect to execute."""
        manager = ModeManager(default_mode=ExecutionMode.ARCHITECT)
        
        new_mode = manager.toggle_mode()
        
        assert new_mode == ExecutionMode.EXECUTE
        assert manager.get_mode() == ExecutionMode.EXECUTE
    
    def test_toggle_mode_from_execute(self):
        """Test toggling from execute to architect."""
        manager = ModeManager(default_mode=ExecutionMode.EXECUTE)
        
        new_mode = manager.toggle_mode()
        
        assert new_mode == ExecutionMode.ARCHITECT
        assert manager.get_mode() == ExecutionMode.ARCHITECT
    
    def test_toggle_mode_multiple_times(self):
        """Test toggling mode multiple times."""
        manager = ModeManager()
        
        assert manager.get_mode() == ExecutionMode.ARCHITECT
        
        manager.toggle_mode()
        assert manager.get_mode() == ExecutionMode.EXECUTE
        
        manager.toggle_mode()
        assert manager.get_mode() == ExecutionMode.ARCHITECT
        
        manager.toggle_mode()
        assert manager.get_mode() == ExecutionMode.EXECUTE
    
    def test_is_architect_mode(self):
        """Test architect mode check."""
        manager = ModeManager(default_mode=ExecutionMode.ARCHITECT)
        
        assert manager.is_architect_mode() is True
        assert manager.is_execute_mode() is False
    
    def test_is_execute_mode(self):
        """Test execute mode check."""
        manager = ModeManager(default_mode=ExecutionMode.EXECUTE)
        
        assert manager.is_execute_mode() is True
        assert manager.is_architect_mode() is False
    
    def test_get_mode_description_current(self):
        """Test getting description for current mode."""
        manager = ModeManager(default_mode=ExecutionMode.ARCHITECT)
        
        description = manager.get_mode_description()
        
        assert "Architect Mode" in description
        assert "Plans and proposes" in description
    
    def test_get_mode_description_specific(self):
        """Test getting description for specific mode."""
        manager = ModeManager()
        
        description = manager.get_mode_description(ExecutionMode.EXECUTE)
        
        assert "Execute Mode" in description
        assert "immediate action" in description
    
    def test_format_status_line_architect(self):
        """Test status line formatting for architect mode."""
        manager = ModeManager(default_mode=ExecutionMode.ARCHITECT)
        
        status = manager.format_status_line()
        
        assert status == "[ARCHITECT]"
    
    def test_format_status_line_execute(self):
        """Test status line formatting for execute mode."""
        manager = ModeManager(default_mode=ExecutionMode.EXECUTE)
        
        status = manager.format_status_line()
        
        assert status == "[EXECUTE]"
    
    def test_should_require_approval_architect(self):
        """Test approval requirement in architect mode."""
        manager = ModeManager(default_mode=ExecutionMode.ARCHITECT)
        
        assert manager.should_require_approval() is True
    
    def test_should_require_approval_execute(self):
        """Test no approval requirement in execute mode."""
        manager = ModeManager(default_mode=ExecutionMode.EXECUTE)
        
        assert manager.should_require_approval() is False
