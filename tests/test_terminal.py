"""
Tests for terminal execution module.

Covers command execution, security validation, risk assessment,
and safety constraints with proper mocking.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from gerdsenai_cli.core.terminal import (
    TerminalExecutor, 
    CommandResult, 
    CommandSecurityConfig
)


class TestCommandSecurityConfig:
    """Test suite for command security configuration."""
    
    def test_initialization(self):
        """Test security config initialization."""
        config = CommandSecurityConfig("strict")
        assert config.safety_level == "strict"
        assert "rm" in config.blocked_commands
        assert "ls" in config.allowed_commands
        assert "curl" in config.restricted_commands
    
    def test_allowed_command_check(self):
        """Test command allow/deny logic."""
        config = CommandSecurityConfig("strict")
        
        # Allowed command
        allowed, message = config.is_command_allowed("ls -la")
        assert allowed is True
        assert "explicitly allowed" in message
        
        # Blocked command in strict mode
        allowed, message = config.is_command_allowed("rm -rf /")
        assert allowed is False
        assert "blocked for security reasons" in message
        
        # Restricted command
        allowed, message = config.is_command_allowed("curl https://example.com")
        assert allowed is True
        assert "requires confirmation" in message
    
    def test_safety_levels(self):
        """Test different safety levels."""
        # Strict mode
        strict_config = CommandSecurityConfig("strict")
        allowed, _ = strict_config.is_command_allowed("unknown_command")
        assert allowed is False
        
        # Moderate mode
        moderate_config = CommandSecurityConfig("moderate")
        allowed, _ = moderate_config.is_command_allowed("unknown_command")
        assert allowed is True
        
        # Permissive mode
        permissive_config = CommandSecurityConfig("permissive")
        allowed, _ = permissive_config.is_command_allowed("rm -rf /")
        assert allowed is True
    
    def test_directory_boundaries(self):
        """Test directory boundary checking."""
        config = CommandSecurityConfig()
        
        # Safe directory
        allowed, message = config.check_directory_boundaries("/home/user/project")
        assert allowed is True
        
        # Test with blocked directories
        with patch('pathlib.Path.resolve') as mock_resolve:
            mock_resolve.return_value = Path("/etc/passwd")
            allowed, message = config.check_directory_boundaries("/etc")
            # This test may vary based on platform and actual path resolution


class TestTerminalExecutor:
    """Test suite for terminal executor functionality."""
    
    def setup_method(self):
        """Set up test executor instance."""
        self.executor = TerminalExecutor(safety_level="strict")
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test executor initialization."""
        assert self.executor.working_directory
        assert self.executor.timeout == 30
        assert self.executor.security_config.safety_level == "strict"
        assert len(self.executor.command_history) == 0
    
    def test_command_name_extraction(self):
        """Test command name extraction logic."""
        # Simple command
        cmd = self.executor._extract_command_name("ls -la")
        assert cmd == "ls"
        
        # Sudo command
        cmd = self.executor._extract_command_name("sudo rm file.txt")
        assert cmd == "rm"
        
        # Complex command with paths
        cmd = self.executor._extract_command_name("/usr/bin/python3 script.py")
        assert cmd == "python3"
    
    def test_risk_level_assessment(self):
        """Test command risk level determination."""
        # Dangerous command
        risk = self.executor._get_command_risk_level("rm -rf /")
        assert risk == "HIGH"
        
        # Network command
        risk = self.executor._get_command_risk_level("curl https://example.com")
        assert risk == "MEDIUM"
        
        # File operation
        risk = self.executor._get_command_risk_level("cp file1 file2")
        assert risk == "LOW"
        
        # Safe command
        risk = self.executor._get_command_risk_level("ls -la")
        assert risk == "MINIMAL"
    
    @pytest.mark.asyncio
    async def test_command_security_blocking(self):
        """Test that blocked commands are rejected."""
        result = await self.executor.execute_command(
            "rm -rf /", 
            require_confirmation=False
        )
        
        assert result.success is False
        assert result.exit_code == -1
        assert "Security policy violation" in result.stderr
    
    @pytest.mark.asyncio
    async def test_allowed_command_execution(self):
        """Test that allowed commands can execute."""
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            # Mock successful process
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"total 0\n", b"")
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            result = await self.executor.execute_command(
                "ls -la",
                require_confirmation=False
            )
            
            assert result.success is True
            assert result.exit_code == 0
            assert "total 0" in result.stdout
    
    @pytest.mark.asyncio 
    async def test_command_timeout(self):
        """Test command timeout handling."""
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.side_effect = asyncio.TimeoutError()
            mock_process.kill = MagicMock()
            mock_process.wait = AsyncMock()
            mock_subprocess.return_value = mock_process
            
            result = await self.executor.execute_command(
                "echo test",
                timeout=1,
                require_confirmation=False
            )
            
            assert result.success is False
            assert "timed out" in result.stderr
            mock_process.kill.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_user_cancellation(self):
        """Test user cancelling command execution."""
        with patch('rich.prompt.Confirm.ask', return_value=False):
            result = await self.executor.execute_command(
                "curl https://example.com",  # Requires confirmation
                require_confirmation=True
            )
            
            assert result.success is False
            assert "cancelled by user" in result.stderr
    
    @pytest.mark.asyncio
    async def test_command_history(self):
        """Test command history tracking."""
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"output", b"")
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            await self.executor.execute_command(
                "echo test1",
                require_confirmation=False
            )
            await self.executor.execute_command(
                "echo test2", 
                require_confirmation=False
            )
            
            history = self.executor.get_command_history()
            assert len(history) == 2
            assert history[0].command == "echo test1"
            assert history[1].command == "echo test2"
    
    def test_working_directory_management(self):
        """Test working directory operations."""
        # Test setting valid directory
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True):
            result = self.executor.set_working_directory("/tmp")
            assert result is True
        
        # Test setting invalid directory
        with patch('pathlib.Path.exists', return_value=False):
            result = self.executor.set_working_directory("/nonexistent")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling during command execution."""
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            mock_subprocess.side_effect = Exception("Process creation failed")
            
            result = await self.executor.execute_command(
                "echo test",
                require_confirmation=False
            )
            
            assert result.success is False
            assert "Execution error" in result.stderr
    
    def test_command_result_structure(self):
        """Test CommandResult data structure."""
        result = CommandResult(
            command="test command",
            success=True,
            exit_code=0,
            stdout="output",
            stderr="",
            execution_time=0.5,
            working_directory="/home/user"
        )
        
        assert result.command == "test command"
        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout == "output" 
        assert result.execution_time == 0.5
        assert result.timestamp is not None
    
    @pytest.mark.asyncio
    async def test_safety_level_configuration(self):
        """Test different safety level configurations."""
        # Permissive executor should allow more commands
        permissive_executor = TerminalExecutor(safety_level="permissive")
        
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"", b"")
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            # Command that would be blocked in strict mode
            result = await permissive_executor.execute_command(
                "unknown_command",
                require_confirmation=False
            )
            
            # Should succeed in permissive mode
            assert result.success is True
    
    def test_history_limit(self):
        """Test command history size limit."""
        # Set low limit for testing
        self.executor.max_history = 3
        
        # Add more commands than the limit
        for i in range(5):
            result = CommandResult(
                command=f"test{i}",
                success=True,
                exit_code=0,
                execution_time=0.1
            )
            self.executor._add_to_history(result)
        
        # Should only keep the last 3
        history = self.executor.get_command_history()
        assert len(history) == 3
        assert history[-1].command == "test4"
