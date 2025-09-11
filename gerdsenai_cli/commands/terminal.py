"""
Terminal command implementations for GerdsenAI CLI.

This module provides slash commands for terminal operations including
command execution, history management, and working directory control.
"""

from typing import Dict, Any, Optional
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .base import BaseCommand
from ..core.terminal import TerminalExecutor, CommandResult
from ..utils.display import show_error, show_info, show_success, show_warning

console = Console()


class RunCommand(BaseCommand):
    """Execute a terminal command with safety features."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.terminal_executor = TerminalExecutor()
    
    @property
    def name(self) -> str:
        return "run"
    
    @property
    def aliases(self) -> list:
        return ["exec", "execute", "cmd"]
    
    @property
    def description(self) -> str:
        return "Execute a terminal command with safety validation"
    
    @property
    def usage(self) -> str:
        return "/run <command> [args...]"
    
    async def execute(self, args: str) -> Dict[str, Any]:
        """Execute a terminal command."""
        if not args.strip():
            show_error("No command specified. Usage: /run <command>")
            return {"success": False}
        
        try:
            # Execute the command
            result = await self.terminal_executor.execute_command(args.strip())
            
            # Format and display the output
            self.terminal_executor.format_command_output(result)
            
            return {
                "success": result.success,
                "exit_code": result.exit_code,
                "command": result.command,
                "execution_time": result.execution_time
            }
            
        except Exception as e:
            show_error(f"Failed to execute command: {e}")
            return {"success": False, "error": str(e)}


class HistoryCommand(BaseCommand):
    """Display command execution history."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Share the same terminal executor instance
        self.terminal_executor = getattr(kwargs.get('run_command'), 'terminal_executor', None)
        if not self.terminal_executor:
            self.terminal_executor = TerminalExecutor()
    
    @property
    def name(self) -> str:
        return "history"
    
    @property
    def aliases(self) -> list:
        return ["hist", "cmd_history"]
    
    @property
    def description(self) -> str:
        return "Display terminal command execution history"
    
    @property
    def usage(self) -> str:
        return "/history [limit]"
    
    async def execute(self, args: str) -> Dict[str, Any]:
        """Display command history."""
        try:
            # Parse limit if provided
            limit = None
            if args.strip():
                try:
                    limit = int(args.strip())
                    if limit <= 0:
                        show_warning("Limit must be a positive number, showing all history")
                        limit = None
                except ValueError:
                    show_warning("Invalid limit format, showing all history")
                    limit = None
            
            # Get command history
            history = self.terminal_executor.get_command_history(limit)
            
            if not history:
                show_info("No command history available")
                return {"success": True, "count": 0}
            
            # Create history table
            table = Table(title="Command History")
            table.add_column("#", style="dim", width=4)
            table.add_column("Command", style="cyan")
            table.add_column("Status", width=8)
            table.add_column("Exit Code", width=10)
            table.add_column("Time", width=8)
            table.add_column("Timestamp", style="dim")
            
            for i, result in enumerate(history, 1):
                status = "[green]SUCCESS[/green]" if result.success else "[red]FAILED[/red]"
                exit_code = str(result.exit_code) if result.exit_code != -1 else "N/A"
                exec_time = f"{result.execution_time:.2f}s"
                timestamp = result.timestamp.strftime("%H:%M:%S")
                
                # Truncate long commands
                command_display = result.command
                if len(command_display) > 50:
                    command_display = command_display[:47] + "..."
                
                table.add_row(
                    str(i),
                    command_display,
                    status,
                    exit_code,
                    exec_time,
                    timestamp
                )
            
            console.print(table)
            
            return {"success": True, "count": len(history)}
            
        except Exception as e:
            show_error(f"Failed to display history: {e}")
            return {"success": False, "error": str(e)}


class ClearHistoryCommand(BaseCommand):
    """Clear command execution history."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Share the same terminal executor instance
        self.terminal_executor = getattr(kwargs.get('run_command'), 'terminal_executor', None)
        if not self.terminal_executor:
            self.terminal_executor = TerminalExecutor()
    
    @property
    def name(self) -> str:
        return "clear_history"
    
    @property
    def aliases(self) -> list:
        return ["clear_hist", "reset_history"]
    
    @property
    def description(self) -> str:
        return "Clear terminal command execution history"
    
    @property
    def usage(self) -> str:
        return "/clear_history"
    
    async def execute(self, args: str) -> Dict[str, Any]:
        """Clear command history."""
        try:
            history_count = len(self.terminal_executor.get_command_history())
            self.terminal_executor.clear_history()
            
            show_success(f"Cleared {history_count} commands from history")
            
            return {"success": True, "cleared_count": history_count}
            
        except Exception as e:
            show_error(f"Failed to clear history: {e}")
            return {"success": False, "error": str(e)}


class WorkingDirectoryCommand(BaseCommand):
    """Display or change the working directory for terminal commands."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Share the same terminal executor instance
        self.terminal_executor = getattr(kwargs.get('run_command'), 'terminal_executor', None)
        if not self.terminal_executor:
            self.terminal_executor = TerminalExecutor()
    
    @property
    def name(self) -> str:
        return "cd"
    
    @property
    def aliases(self) -> list:
        return ["cwd", "pwd", "chdir"]
    
    @property
    def description(self) -> str:
        return "Display or change working directory for terminal commands"
    
    @property
    def usage(self) -> str:
        return "/cd [directory]"
    
    async def execute(self, args: str) -> Dict[str, Any]:
        """Change or display working directory."""
        try:
            if not args.strip():
                # Display current working directory
                current_dir = self.terminal_executor.get_working_directory()
                show_info(f"Current working directory: {current_dir}")
                return {"success": True, "current_directory": current_dir}
            
            # Change working directory
            new_dir = args.strip()
            
            # Handle relative paths and special cases
            if new_dir == "~":
                new_dir = Path.home()
            elif new_dir == "..":
                new_dir = Path(self.terminal_executor.get_working_directory()).parent
            else:
                new_dir = Path(new_dir)
            
            # Attempt to change directory
            success = self.terminal_executor.set_working_directory(str(new_dir))
            
            if success:
                new_path = self.terminal_executor.get_working_directory()
                show_success(f"Changed working directory to: {new_path}")
                return {"success": True, "new_directory": new_path}
            else:
                show_error(f"Failed to change to directory: {new_dir}")
                return {"success": False, "error": "Directory not found or not accessible"}
            
        except Exception as e:
            show_error(f"Failed to change directory: {e}")
            return {"success": False, "error": str(e)}


class TerminalStatusCommand(BaseCommand):
    """Display terminal executor status and configuration."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Share the same terminal executor instance
        self.terminal_executor = getattr(kwargs.get('run_command'), 'terminal_executor', None)
        if not self.terminal_executor:
            self.terminal_executor = TerminalExecutor()
    
    @property
    def name(self) -> str:
        return "terminal_status"
    
    @property
    def aliases(self) -> list:
        return ["term_status", "terminal_info"]
    
    @property
    def description(self) -> str:
        return "Display terminal executor status and configuration"
    
    @property
    def usage(self) -> str:
        return "/terminal_status"
    
    async def execute(self, args: str) -> Dict[str, Any]:
        """Display terminal status."""
        try:
            current_dir = self.terminal_executor.get_working_directory()
            history_count = len(self.terminal_executor.get_command_history())
            
            status_text = Text()
            status_text.append("Working Directory: ", style="bold")
            status_text.append(f"{current_dir}\n", style="cyan")
            status_text.append("Command History: ", style="bold")
            status_text.append(f"{history_count} commands\n", style="yellow")
            status_text.append("Default Timeout: ", style="bold")
            status_text.append(f"{self.terminal_executor.timeout}s\n", style="green")
            status_text.append("Platform: ", style="bold")
            status_text.append("Windows" if self.terminal_executor.is_windows else "Unix-like", style="blue")
            
            panel = Panel(
                status_text,
                title="Terminal Executor Status",
                border_style="blue"
            )
            
            console.print(panel)
            
            return {
                "success": True,
                "working_directory": current_dir,
                "history_count": history_count,
                "timeout": self.terminal_executor.timeout,
                "platform": "Windows" if self.terminal_executor.is_windows else "Unix-like"
            }
            
        except Exception as e:
            show_error(f"Failed to get terminal status: {e}")
            return {"success": False, "error": str(e)}
