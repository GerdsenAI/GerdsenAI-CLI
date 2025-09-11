"""
System-related commands for GerdsenAI CLI.

This module contains commands for system status, configuration, and general CLI operations.
"""

from typing import Any, Dict
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .base import BaseCommand, CommandCategory, CommandResult, CommandArgument
from ..utils.display import show_error, show_info, show_success, show_warning

console = Console()


class HelpCommand(BaseCommand):
    """Display help information for commands."""
    
    @property
    def name(self) -> str:
        return "help"
    
    @property
    def description(self) -> str:
        return "Show help for commands"
    
    @property
    def category(self) -> CommandCategory:
        return CommandCategory.SYSTEM
    
    @property
    def aliases(self) -> list[str]:
        return ["h", "?"]
    
    def _define_arguments(self) -> Dict[str, CommandArgument]:
        return {
            "command": CommandArgument(
                name="command",
                description="Specific command to show help for",
                required=False
            )
        }
    
    async def execute(self, args: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Execute help command."""
        command_name = args.get("command")
        parser = context.get("parser")
        
        if not parser:
            return CommandResult(success=False, message="Command parser not available")
        
        parser.show_help(command_name)
        return CommandResult(success=True)


class ExitCommand(BaseCommand):
    """Exit the application."""
    
    @property
    def name(self) -> str:
        return "exit"
    
    @property
    def description(self) -> str:
        return "Exit the application"
    
    @property
    def category(self) -> CommandCategory:
        return CommandCategory.SYSTEM
    
    @property
    def aliases(self) -> list[str]:
        return ["quit", "q"]
    
    async def execute(self, args: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Execute exit command."""
        console.print("\n👋 [bright_cyan]Goodbye![/bright_cyan]")
        return CommandResult(success=True, should_exit=True)


class StatusCommand(BaseCommand):
    """Show system status."""
    
    @property
    def name(self) -> str:
        return "status"
    
    @property
    def description(self) -> str:
        return "Show system status and health information"
    
    @property
    def category(self) -> CommandCategory:
        return CommandCategory.SYSTEM
    
    @property
    def aliases(self) -> list[str]:
        return ["stat"]
    
    def _define_arguments(self) -> Dict[str, CommandArgument]:
        return {
            "verbose": CommandArgument(
                name="verbose",
                description="Show detailed status information",
                required=False,
                arg_type=bool,
                default=False
            )
        }
    
    async def execute(self, args: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Execute status command."""
        verbose = args.get("verbose", False)
        
        console.print("\n📊 [bold cyan]System Status[/bold cyan]\n")
        
        # LLM Client Status
        llm_client = context.get("llm_client")
        if llm_client:
            with console.status("[bold green]Checking LLM status...", spinner="dots"):
                health = await llm_client.health_check()
            
            status = "✅ Connected" if health["connected"] else "❌ Disconnected"
            console.print(f"  LLM Connection:     [bold]{status}[/bold]")
            console.print(f"  Server URL:         [bold]{health['server_url']}[/bold]")
            
            if health["response_time_ms"]:
                console.print(f"  Response Time:      [bold]{health['response_time_ms']}ms[/bold]")
            
            console.print(f"  Models Available:   [bold]{health['models_available']}[/bold]")
            
            if health["error"]:
                console.print(f"  Error:              [bold red]{health['error']}[/bold red]")
        else:
            console.print("  LLM Client:         [bold red]Not initialized[/bold red]")
        
        # Agent Status
        agent = context.get("agent")
        if agent:
            stats = agent.get_agent_stats()
            console.print(f"  AI Agent:           [bold green]✅ Ready[/bold green]")
            console.print(f"  Actions Performed:  [bold]{stats['actions_performed']}[/bold]")
            console.print(f"  Files Indexed:      [bold]{stats['project_files_indexed']}[/bold]")
            
            if verbose:
                console.print(f"\n🤖 [bold cyan]Agent Details:[/bold cyan]")
                console.print(f"  Files Modified:     [bold]{stats['files_modified']}[/bold]")
                console.print(f"  Context Builds:     [bold]{stats['context_builds']}[/bold]")
                console.print(f"  Conversation:       [bold]{stats['conversation_length']} messages[/bold]")
                
                if stats['last_action']:
                    console.print(f"  Last Action:        [bold]{stats['last_action']}[/bold]")
        else:
            console.print("  AI Agent:           [bold red]❌ Not initialized[/bold red]")
        
        # Command Parser Status
        parser = context.get("parser")
        if parser and verbose:
            parser_stats = parser.get_status()
            console.print(f"\n⚙️  [bold cyan]Parser Status:[/bold cyan]")
            console.print(f"  Commands Loaded:    [bold]{parser_stats['total_commands']}[/bold]")
            console.print(f"  Aliases Available:  [bold]{parser_stats['total_aliases']}[/bold]")
        
        console.print()
        return CommandResult(success=True)


class ConfigCommand(BaseCommand):
    """Show or modify configuration."""
    
    @property
    def name(self) -> str:
        return "config"
    
    @property
    def description(self) -> str:
        return "Show current configuration or modify settings"
    
    @property
    def category(self) -> CommandCategory:
        return CommandCategory.SYSTEM
    
    def _define_arguments(self) -> Dict[str, CommandArgument]:
        return {
            "action": CommandArgument(
                name="action",
                description="Action to perform",
                required=False,
                choices=["show", "set", "get"],
                default="show"
            ),
            "key": CommandArgument(
                name="key",
                description="Configuration key to get/set",
                required=False
            ),
            "value": CommandArgument(
                name="value", 
                description="Value to set (for 'set' action)",
                required=False
            )
        }
    
    async def execute(self, args: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Execute config command."""
        action = args.get("action", "show")
        key = args.get("key")
        value = args.get("value")
        
        settings = context.get("settings")
        config_manager = context.get("config_manager")
        
        if not settings:
            return CommandResult(success=False, message="Settings not available")
        
        if action == "show":
            await self._show_config(settings, context)
        elif action == "get":
            if not key:
                return CommandResult(success=False, message="Key required for 'get' action")
            await self._get_config_value(settings, key)
        elif action == "set":
            if not key or not value:
                return CommandResult(success=False, message="Both key and value required for 'set' action")
            if not config_manager:
                return CommandResult(success=False, message="Config manager not available")
            await self._set_config_value(settings, config_manager, key, value)
        
        return CommandResult(success=True)
    
    async def _show_config(self, settings, context: Dict[str, Any]) -> None:
        """Show full configuration."""
        console.print("\n⚙️  [bold cyan]Current Configuration[/bold cyan]\n")
        
        # Basic settings
    console.print(f"  LLM Protocol:       [bold]{getattr(settings, 'protocol', 'http')}[/bold]")
    console.print(f"  LLM Host:           [bold]{getattr(settings, 'llm_host', 'localhost')}[/bold]")
    console.print(f"  LLM Port:           [bold]{getattr(settings, 'llm_port', 11434)}[/bold]")
    console.print(f"  LLM Server URL:     [bold]{settings.llm_server_url}[/bold]")
    console.print(f"  Current Model:      [bold]{settings.current_model or 'Not set'}[/bold]")
    console.print(f"  API Timeout:        [bold]{settings.api_timeout}s[/bold]")
        
        # Connection status
        llm_client = context.get("llm_client")
        if llm_client:
            status = "✅ Connected" if llm_client.is_connected else "❌ Disconnected" 
            console.print(f"  Connection:         [bold]{status}[/bold]")
        
        # Agent status
        agent = context.get("agent")
        if agent:
            stats = agent.get_agent_stats()
            status = "✅ Ready" if agent else "❌ Not initialized"
            console.print(f"  AI Agent:           [bold]{status}[/bold]")
            console.print(f"  Project Files:      [bold]{stats['project_files_indexed']}[/bold]")
        
        # User preferences
        if settings.user_preferences:
            console.print(f"\n  [bold cyan]User Preferences:[/bold cyan]")
            for key, value in settings.user_preferences.items():
                console.print(f"    {key}: [bold]{value}[/bold]")
        
        console.print()
    
    async def _get_config_value(self, settings, key: str) -> None:
        """Get specific configuration value."""
        value = getattr(settings, key, None)
        if value is None and settings.user_preferences:
            value = settings.user_preferences.get(key)
        
        if value is not None:
            console.print(f"\n[bold cyan]{key}:[/bold cyan] {value}\n")
        else:
            show_warning(f"Configuration key '{key}' not found")
    
    async def _set_config_value(self, settings, config_manager, key: str, value: str) -> None:
        """Set configuration value."""
        # Simple implementation - in practice you'd want more validation
        if hasattr(settings, key):
            # Try to convert value to appropriate type
            current_value = getattr(settings, key)
            if isinstance(current_value, bool):
                value = value.lower() in {'true', '1', 'yes', 'on'}
            elif isinstance(current_value, int):
                value = int(value)
            elif isinstance(current_value, float):
                value = float(value)
            
            setattr(settings, key, value)
        else:
            # Store in user preferences
            if not settings.user_preferences:
                settings.user_preferences = {}
            settings.user_preferences[key] = value
        
        # Save settings
        success = await config_manager.save_settings(settings)
        if success:
            show_success(f"Configuration updated: {key} = {value}")
        else:
            show_error("Failed to save configuration")


class DebugCommand(BaseCommand):
    """Toggle debug mode."""
    
    @property
    def name(self) -> str:
        return "debug"
    
    @property
    def description(self) -> str:
        return "Toggle debug mode on/off"
    
    @property
    def category(self) -> CommandCategory:
        return CommandCategory.SYSTEM
    
    def _define_arguments(self) -> Dict[str, CommandArgument]:
        return {
            "mode": CommandArgument(
                name="mode",
                description="Debug mode state",
                required=False,
                choices=["on", "off", "toggle"],
                default="toggle"
            )
        }
    
    async def execute(self, args: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Execute debug command."""
        mode = args.get("mode", "toggle")
        
        # Get current debug state from context
        current_debug = context.get("debug", False)
        
        if mode == "on":
            new_debug = True
        elif mode == "off":
            new_debug = False
        else:  # toggle
            new_debug = not current_debug
        
        # Update context
        context["debug"] = new_debug
        
        # Update app debug state if available
        app = context.get("app")
        if app:
            app.debug = new_debug
        
        status = "enabled" if new_debug else "disabled"
        show_success(f"Debug mode {status}")
        
        return CommandResult(success=True, data={"debug": new_debug})


class SetupCommand(BaseCommand):
    """Interactive reconfiguration of LLM server connection."""

    @property
    def name(self) -> str:
        return "setup"

    @property
    def description(self) -> str:
        return "Run interactive setup to change LLM protocol/host/port and optionally model"

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.SYSTEM

    def _define_arguments(self) -> Dict[str, CommandArgument]:
        return {
            "apply": CommandArgument(
                name="apply",
                description="Automatically apply defaults without prompts",
                required=False,
                arg_type=bool,
                default=False
            )
        }

    async def execute(self, args: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        from rich.prompt import Prompt
        settings = context.get("settings")
        config_manager = context.get("config_manager")
        if not settings or not config_manager:
            return CommandResult(success=False, message="Settings or config manager unavailable")

        auto_apply = args.get("apply", False)

        try:
            if auto_apply:
                protocol = settings.protocol
                host = settings.llm_host
                port = settings.llm_port
            else:
                protocol = Prompt.ask("Protocol (http/https)", choices=["http", "https"], default=settings.protocol)
                host = Prompt.ask("Host", default=settings.llm_host)
                port_str = Prompt.ask("Port", default=str(settings.llm_port))
                try:
                    port = int(port_str)
                except ValueError:
                    show_warning("Invalid port - keeping previous value")
                    port = settings.llm_port

            # Update settings
            settings.protocol = protocol
            settings.llm_host = host
            settings.llm_port = port
            # model_validator will sync full URL on revalidation via assignment
            settings.llm_server_url = f"{protocol}://{host}:{port}"

            # Optionally test connection
            llm_client = context.get("llm_client")
            if llm_client:
                llm_client.base_url = settings.llm_server_url
                show_info("Testing connection with new settings...")
                connected = await llm_client.connect()
                if connected:
                    show_success("Connection successful")
                else:
                    show_warning("Connection failed with new settings")

            # Save
            success = await config_manager.save_settings(settings)
            if success:
                show_success("Settings saved")
                return CommandResult(success=True)
            else:
                return CommandResult(success=False, message="Failed to save settings")
        except Exception as e:
            show_error(f"Setup failed: {e}")
            return CommandResult(success=False, message=str(e))
