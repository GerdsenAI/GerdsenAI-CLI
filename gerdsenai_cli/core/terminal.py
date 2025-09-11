"""
Terminal execution module for GerdsenAI CLI.

This module provides safe terminal command execution with validation,
user confirmation, and comprehensive logging capabilities.
"""

import asyncio
import os
import platform
import shlex
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from rich.console import Console
from rich.prompt import Confirm
from rich.text import Text
from rich.panel import Panel

from ..utils.display import show_error, show_warning, show_info, show_success

# Security configuration for command execution
class CommandSecurityConfig:
    """Configuration for terminal command security."""
    
    def __init__(self, safety_level: str = "strict"):
        self.safety_level = safety_level  # "strict", "moderate", "permissive"
        
        # Commands that are always blocked in strict mode
        self.blocked_commands = {
            'rm', 'del', 'rmdir', 'rd', 'format', 'fdisk', 'mkfs',
            'dd', 'shred', 'wipe', 'shutdown', 'reboot', 'halt', 
            'poweroff', 'init', 'passwd', 'su', 'useradd', 'userdel',
            'usermod', 'groupadd', 'groupdel'
        }
        
        # Commands that are allowed without confirmation in all modes
        self.allowed_commands = {
            'ls', 'dir', 'pwd', 'cd', 'cat', 'type', 'head', 'tail',
            'echo', 'printf', 'grep', 'find', 'which', 'where', 'whoami',
            'date', 'uptime', 'ps', 'top', 'htop', 'df', 'du', 'free',
            'git', 'node', 'npm', 'pip', 'python', 'python3', 'java',
            'javac', 'gcc', 'make', 'cmake', 'go', 'rust', 'cargo'
        }
        
        # Commands that require confirmation but are allowed
        self.restricted_commands = {
            'chmod', 'chown', 'chgrp', 'kill', 'killall', 'pkill',
            'cp', 'mv', 'copy', 'move', 'rename', 'ln', 'link',
            'curl', 'wget', 'ssh', 'scp', 'rsync', 'ftp', 'sftp',
            'telnet', 'nc', 'netcat', 'ping', 'traceroute', 'nmap'
        }
        
        # Directory boundaries (paths that operations cannot go outside)
        self.allowed_directories = set()
        self.blocked_directories = {
            '/etc', '/boot', '/sys', '/proc', '/dev', '/var/log',
            'C:\\Windows', 'C:\\Program Files', 'C:\\Program Files (x86)'
        }
    
    def is_command_allowed(self, command: str) -> Tuple[bool, str]:
        """Check if a command is allowed based on security configuration."""
        cmd_name = command.strip().split()[0] if command.strip() else ""
        cmd_base = os.path.basename(cmd_name).lower()
        
        # Remove common prefixes
        if cmd_base.startswith('sudo '):
            parts = command.strip().split()
            if len(parts) > 1:
                cmd_base = os.path.basename(parts[1]).lower()
        
        # Check blocked commands
        if cmd_base in self.blocked_commands:
            if self.safety_level == "strict":
                return False, f"Command '{cmd_base}' is blocked for security reasons"
            elif self.safety_level == "moderate":
                return True, f"Command '{cmd_base}' requires confirmation (security risk)"
        
        # Check explicitly allowed commands
        if cmd_base in self.allowed_commands:
            return True, "Command is explicitly allowed"
        
        # Check restricted commands
        if cmd_base in self.restricted_commands:
            return True, f"Command '{cmd_base}' requires confirmation"
        
        # Default behavior based on safety level
        if self.safety_level == "strict":
            return False, f"Command '{cmd_base}' is not in the allowed list"
        elif self.safety_level == "moderate":
            return True, f"Command '{cmd_base}' requires confirmation (unknown command)"
        else:  # permissive
            return True, "Command allowed in permissive mode"
    
    def check_directory_boundaries(self, working_dir: str) -> Tuple[bool, str]:
        """Check if the working directory is within allowed boundaries."""
        try:
            work_path = Path(working_dir).resolve()
            
            # Check blocked directories
            for blocked_dir in self.blocked_directories:
                try:
                    blocked_path = Path(blocked_dir).resolve()
                    if work_path.is_relative_to(blocked_path):
                        return False, f"Directory '{working_dir}' is in blocked path '{blocked_dir}'"
                except (OSError, ValueError):
                    continue
            
            # If allowed directories are specified, check them
            if self.allowed_directories:
                for allowed_dir in self.allowed_directories:
                    try:
                        allowed_path = Path(allowed_dir).resolve()
                        if work_path.is_relative_to(allowed_path):
                            return True, "Directory is within allowed boundaries"
                    except (OSError, ValueError):
                        continue
                return False, f"Directory '{working_dir}' is outside allowed boundaries"
            
            return True, "Directory boundaries check passed"
            
        except Exception as e:
            return False, f"Error checking directory boundaries: {e}"

console = Console()


class CommandResult:
    """Result of a terminal command execution."""
    
    def __init__(
        self,
        command: str,
        success: bool,
        exit_code: int,
        stdout: str = "",
        stderr: str = "",
        execution_time: float = 0.0,
        working_directory: Optional[str] = None
    ):
        self.command = command
        self.success = success
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.execution_time = execution_time
        self.working_directory = working_directory
        self.timestamp = datetime.now()


class TerminalExecutor:
    """
    Safe terminal command executor with validation and logging.
    """
    
    # Dangerous commands that require confirmation
    DANGEROUS_COMMANDS = {
        'rm', 'del', 'rmdir', 'rd', 'format', 'fdisk', 'mkfs',
        'dd', 'shred', 'wipe', 'kill', 'killall', 'pkill',
        'shutdown', 'reboot', 'halt', 'poweroff', 'init',
        'chmod', 'chown', 'chgrp', 'passwd', 'su', 'sudo',
        'useradd', 'userdel', 'usermod', 'groupadd', 'groupdel'
    }
    
    # Network commands that should prompt user
    NETWORK_COMMANDS = {
        'curl', 'wget', 'ssh', 'scp', 'rsync', 'ftp', 'sftp',
        'telnet', 'nc', 'netcat', 'ping', 'traceroute', 'nmap'
    }
    
    # File operation commands
    FILE_OPERATION_COMMANDS = {
        'cp', 'mv', 'copy', 'move', 'rename', 'ln', 'link'
    }
    
    def __init__(
        self, 
        working_directory: Optional[str] = None, 
        timeout: int = 30,
        safety_level: str = "strict"
    ):
        """
        Initialize the terminal executor.
        
        Args:
            working_directory: Default working directory for commands
            timeout: Default timeout for command execution in seconds
            safety_level: Security level ("strict", "moderate", "permissive")
        """
        self.working_directory = working_directory or os.getcwd()
        self.timeout = timeout
        self.command_history: List[CommandResult] = []
        self.max_history = 100
        
        # Security configuration
        self.security_config = CommandSecurityConfig(safety_level)
        
        # Platform-specific settings
        self.is_windows = platform.system() == "Windows"
        self.shell = self._get_default_shell()
    
    def _get_default_shell(self) -> str:
        """Get the default shell for the current platform."""
        if self.is_windows:
            return os.environ.get('COMSPEC', 'cmd.exe')
        else:
            return os.environ.get('SHELL', '/bin/bash')
    
    def _extract_command_name(self, command: str) -> str:
        """Extract the main command name from a command string."""
        try:
            # Handle shell-specific syntax
            if command.strip().startswith('sudo '):
                # For sudo commands, get the actual command being executed
                parts = shlex.split(command.strip())
                if len(parts) > 1:
                    return parts[1]
            
            # Parse the command to get the first part
            parts = shlex.split(command.strip())
            if parts:
                return os.path.basename(parts[0])
            return ""
        except (ValueError, IndexError):
            # If parsing fails, try simple split
            return command.strip().split()[0] if command.strip() else ""
    
    def _is_dangerous_command(self, command: str) -> bool:
        """Check if a command is potentially dangerous."""
        cmd_name = self._extract_command_name(command)
        return cmd_name.lower() in self.DANGEROUS_COMMANDS
    
    def _is_network_command(self, command: str) -> bool:
        """Check if a command involves network operations."""
        cmd_name = self._extract_command_name(command)
        return cmd_name.lower() in self.NETWORK_COMMANDS
    
    def _is_file_operation(self, command: str) -> bool:
        """Check if a command involves file operations."""
        cmd_name = self._extract_command_name(command)
        return cmd_name.lower() in self.FILE_OPERATION_COMMANDS
    
    def _get_command_risk_level(self, command: str) -> str:
        """Determine the risk level of a command."""
        if self._is_dangerous_command(command):
            return "HIGH"
        elif self._is_network_command(command):
            return "MEDIUM"
        elif self._is_file_operation(command):
            return "LOW"
        else:
            return "MINIMAL"
    
    def _show_command_preview(self, command: str, working_dir: str) -> None:
        """Show a preview of the command before execution."""
        risk_level = self._get_command_risk_level(command)
        
        # Color code based on risk level
        risk_colors = {
            "HIGH": "red",
            "MEDIUM": "yellow", 
            "LOW": "cyan",
            "MINIMAL": "green"
        }
        
        preview_text = Text()
        preview_text.append("Command: ", style="bold")
        preview_text.append(f"{command}\n", style="cyan")
        preview_text.append("Working Directory: ", style="bold")
        preview_text.append(f"{working_dir}\n", style="dim")
        preview_text.append("Risk Level: ", style="bold")
        preview_text.append(risk_level, style=risk_colors.get(risk_level, "white"))
        
        panel = Panel(
            preview_text,
            title="Command Preview",
            border_style=risk_colors.get(risk_level, "white")
        )
        
        console.print(panel)
    
    async def _get_user_confirmation(self, command: str, risk_level: str) -> bool:
        """Get user confirmation for command execution."""
        if risk_level == "MINIMAL":
            return True
        
        risk_messages = {
            "HIGH": "This command could potentially harm your system or data.",
            "MEDIUM": "This command will make network connections.",
            "LOW": "This command will modify files or directories."
        }
        
        message = risk_messages.get(risk_level, "This command requires confirmation.")
        show_warning(message)
        
        return Confirm.ask("Do you want to execute this command?", default=False)
    
    async def execute_command(
        self,
        command: str,
        working_directory: Optional[str] = None,
        timeout: Optional[int] = None,
        require_confirmation: bool = True
    ) -> CommandResult:
        """
        Execute a terminal command safely.
        
        Args:
            command: The command to execute
            working_directory: Directory to execute the command in
            timeout: Timeout for the command in seconds
            require_confirmation: Whether to require user confirmation
            
        Returns:
            CommandResult with execution details
        """
        # Use provided working directory or default
        work_dir = working_directory or self.working_directory
        cmd_timeout = timeout or self.timeout
        
        # Security check: Validate command against allow/deny lists
        is_allowed, security_message = self.security_config.is_command_allowed(command)
        if not is_allowed:
            show_error(f"Command blocked: {security_message}")
            return CommandResult(
                command=command,
                success=False,
                exit_code=-1,
                stderr=f"Security policy violation: {security_message}",
                working_directory=work_dir
            )
        
        # Security check: Validate working directory boundaries
        dir_allowed, dir_message = self.security_config.check_directory_boundaries(work_dir)
        if not dir_allowed:
            show_error(f"Directory access blocked: {dir_message}")
            return CommandResult(
                command=command,
                success=False,
                exit_code=-1,
                stderr=f"Directory boundary violation: {dir_message}",
                working_directory=work_dir
            )
        
        # Show command preview
        self._show_command_preview(command, work_dir)
        
        # Check if confirmation is needed
        if require_confirmation:
            risk_level = self._get_command_risk_level(command)
            # Also require confirmation if security config indicates it
            needs_confirmation = (
                risk_level != "MINIMAL" or 
                "requires confirmation" in security_message.lower()
            )
            
            if needs_confirmation and not await self._get_user_confirmation(command, risk_level):
                show_info("Command execution cancelled by user.")
                return CommandResult(
                    command=command,
                    success=False,
                    exit_code=-1,
                    stderr="Execution cancelled by user",
                    working_directory=work_dir
                )
        
        # Execute the command
        start_time = time.time()
        
        try:
            # Prepare the command for execution
            if self.is_windows:
                # On Windows, use the shell directly
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=work_dir
                )
            else:
                # On Unix-like systems, use the shell
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=work_dir,
                    executable=self.shell
                )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=cmd_timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                execution_time = time.time() - start_time
                
                result = CommandResult(
                    command=command,
                    success=False,
                    exit_code=-1,
                    stderr=f"Command timed out after {cmd_timeout} seconds",
                    execution_time=execution_time,
                    working_directory=work_dir
                )
                self._add_to_history(result)
                return result
            
            execution_time = time.time() - start_time
            
            # Decode output
            stdout_text = stdout.decode('utf-8', errors='replace') if stdout else ""
            stderr_text = stderr.decode('utf-8', errors='replace') if stderr else ""
            
            # Create result
            result = CommandResult(
                command=command,
                success=process.returncode == 0,
                exit_code=process.returncode,
                stdout=stdout_text,
                stderr=stderr_text,
                execution_time=execution_time,
                working_directory=work_dir
            )
            
            self._add_to_history(result)
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            result = CommandResult(
                command=command,
                success=False,
                exit_code=-1,
                stderr=f"Execution error: {str(e)}",
                execution_time=execution_time,
                working_directory=work_dir
            )
            
            self._add_to_history(result)
            return result
    
    def _add_to_history(self, result: CommandResult) -> None:
        """Add a command result to the history."""
        self.command_history.append(result)
        
        # Limit history size
        if len(self.command_history) > self.max_history:
            self.command_history = self.command_history[-self.max_history:]
    
    def get_command_history(self, limit: Optional[int] = None) -> List[CommandResult]:
        """Get command execution history."""
        if limit:
            return self.command_history[-limit:]
        return self.command_history.copy()
    
    def clear_history(self) -> None:
        """Clear the command history."""
        self.command_history.clear()
    
    def set_working_directory(self, directory: str) -> bool:
        """
        Set the working directory for future commands.
        
        Args:
            directory: Path to the new working directory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            path = Path(directory).resolve()
            if path.exists() and path.is_dir():
                self.working_directory = str(path)
                return True
            return False
        except Exception:
            return False
    
    def get_working_directory(self) -> str:
        """Get the current working directory."""
        return self.working_directory
    
    def format_command_output(self, result: CommandResult) -> None:
        """Format and display command output."""
        if result.success:
            show_success(f"Command completed in {result.execution_time:.2f}s")
        else:
            show_error(f"Command failed with exit code {result.exit_code}")
        
        # Display stdout if present
        if result.stdout.strip():
            console.print(Panel(
                result.stdout.strip(),
                title="Output",
                border_style="green" if result.success else "red"
            ))
        
        # Display stderr if present and command failed
        if result.stderr.strip() and not result.success:
            console.print(Panel(
                result.stderr.strip(),
                title="Error Output",
                border_style="red"
            ))
