"""
System-related commands for GerdsenAI CLI.

This module contains commands for system status, configuration, and general CLI operations.
"""

import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel

from ..utils.display import show_error, show_info, show_success, show_warning
from .base import BaseCommand, CommandArgument, CommandCategory, CommandResult

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

    def _define_arguments(self) -> dict[str, CommandArgument]:
        return {
            "command": CommandArgument(
                name="command",
                description="Specific command to show help for",
                required=False,
            )
        }

    async def execute(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
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

    async def execute(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
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

    def _define_arguments(self) -> dict[str, CommandArgument]:
        return {
            "verbose": CommandArgument(
                name="verbose",
                description="Show detailed status information",
                required=False,
                arg_type=bool,
                default=False,
            )
        }

    async def execute(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
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
                console.print(
                    f"  Response Time:      [bold]{health['response_time_ms']}ms[/bold]"
                )

            console.print(
                f"  Models Available:   [bold]{health['models_available']}[/bold]"
            )

            if health["error"]:
                console.print(
                    f"  Error:              [bold red]{health['error']}[/bold red]"
                )
        else:
            console.print("  LLM Client:         [bold red]Not initialized[/bold red]")

        # Agent Status
        agent = context.get("agent")
        if agent:
            stats = agent.get_agent_stats()
            console.print("  AI Agent:           [bold green]✅ Ready[/bold green]")
            console.print(
                f"  Actions Performed:  [bold]{stats['actions_performed']}[/bold]"
            )
            console.print(
                f"  Files Indexed:      [bold]{stats['project_files_indexed']}[/bold]"
            )

            if verbose:
                console.print("\n🤖 [bold cyan]Agent Details:[/bold cyan]")
                console.print(
                    f"  Files Modified:     [bold]{stats['files_modified']}[/bold]"
                )
                console.print(
                    f"  Context Builds:     [bold]{stats['context_builds']}[/bold]"
                )
                console.print(
                    f"  Conversation:       [bold]{stats['conversation_length']} messages[/bold]"
                )

                if stats["last_action"]:
                    console.print(
                        f"  Last Action:        [bold]{stats['last_action']}[/bold]"
                    )
        else:
            console.print(
                "  AI Agent:           [bold red]❌ Not initialized[/bold red]"
            )

        # Command Parser Status
        parser = context.get("parser")
        if parser and verbose:
            parser_stats = parser.get_status()
            console.print("\n⚙️  [bold cyan]Parser Status:[/bold cyan]")
            console.print(
                f"  Commands Loaded:    [bold]{parser_stats['total_commands']}[/bold]"
            )
            console.print(
                f"  Aliases Available:  [bold]{parser_stats['total_aliases']}[/bold]"
            )

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

    def _define_arguments(self) -> dict[str, CommandArgument]:
        return {
            "action": CommandArgument(
                name="action",
                description="Action to perform",
                required=False,
                choices=["show", "set", "get"],
                default="show",
            ),
            "key": CommandArgument(
                name="key", description="Configuration key to get/set", required=False
            ),
            "value": CommandArgument(
                name="value",
                description="Value to set (for 'set' action)",
                required=False,
            ),
        }

    async def execute(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
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
                return CommandResult(
                    success=False, message="Key required for 'get' action"
                )
            await self._get_config_value(settings, key)
        elif action == "set":
            if not key or not value:
                return CommandResult(
                    success=False,
                    message="Both key and value required for 'set' action",
                )
            if not config_manager:
                return CommandResult(
                    success=False, message="Config manager not available"
                )
            await self._set_config_value(settings, config_manager, key, value)

        return CommandResult(success=True)

    async def _show_config(self, settings, context: dict[str, Any]) -> None:
        """Show full configuration."""
        console.print("\n⚙️  [bold cyan]Current Configuration[/bold cyan]\n")

        # Basic settings
        console.print(
            f"  LLM Protocol:       [bold]{getattr(settings, 'protocol', 'http')}[/bold]"
        )
        console.print(
            f"  LLM Host:           [bold]{getattr(settings, 'llm_host', 'localhost')}[/bold]"
        )
        console.print(
            f"  LLM Port:           [bold]{getattr(settings, 'llm_port', 11434)}[/bold]"
        )
        console.print(f"  LLM Server URL:     [bold]{settings.llm_server_url}[/bold]")
        console.print(
            f"  Current Model:      [bold]{settings.current_model or 'Not set'}[/bold]"
        )
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
            console.print(
                f"  Project Files:      [bold]{stats['project_files_indexed']}[/bold]"
            )

        # User preferences
        if settings.user_preferences:
            console.print("\n  [bold cyan]User Preferences:[/bold cyan]")
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

    async def _set_config_value(
        self, settings, config_manager, key: str, value: str
    ) -> None:
        """Set configuration value."""
        # Simple implementation - in practice you'd want more validation
        if hasattr(settings, key):
            # Try to convert value to appropriate type
            current_value = getattr(settings, key)
            converted_value: Any = value
            if isinstance(current_value, bool):
                converted_value = value.lower() in {"true", "1", "yes", "on"}
            elif isinstance(current_value, int):
                converted_value = int(value)
            elif isinstance(current_value, float):
                converted_value = float(value)

            setattr(settings, key, converted_value)
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

    def _define_arguments(self) -> dict[str, CommandArgument]:
        return {
            "mode": CommandArgument(
                name="mode",
                description="Debug mode state",
                required=False,
                choices=["on", "off", "toggle"],
                default="toggle",
            )
        }

    async def execute(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
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


class AboutCommand(BaseCommand):
    """Show version and system information for troubleshooting."""

    @property
    def name(self) -> str:
        return "about"

    @property
    def description(self) -> str:
        return "Show version and system information for troubleshooting"

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.SYSTEM

    @property
    def aliases(self) -> list[str]:
        return ["version", "info"]

    def _define_arguments(self) -> dict[str, CommandArgument]:
        return {
            "detailed": CommandArgument(
                name="detailed",
                description="Show detailed system and environment information",
                required=False,
                arg_type=bool,
                default=False,
            )
        }

    async def execute(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
        """Execute about command."""
        detailed = args.get("detailed", False)

        # Get version info
        try:
            from .. import __version__
        except ImportError:
            __version__ = "0.1.0-dev"

        console.print("\n🔧 [bold cyan]GerdsenAI CLI - About[/bold cyan]\n")

        # Basic version information
        console.print(f"  Version:            [bold green]{__version__}[/bold green]")
        console.print(f"  Python Version:     [bold]{sys.version.split()[0]}[/bold]")
        console.print(
            f"  Platform:           [bold]{platform.system()} {platform.release()}[/bold]"
        )
        console.print(f"  Architecture:       [bold]{platform.machine()}[/bold]")

        # Current timestamp
        console.print(
            f"  Current Time:       [bold]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/bold]"
        )

        if detailed:
            console.print("\n📋 [bold cyan]Detailed System Information[/bold cyan]")

            # Python details
            console.print(f"  Python Executable:  [bold]{sys.executable}[/bold]")
            console.print(f"  Python Path:        [dim]{sys.path[0]}[/dim]")

            # Platform details
            console.print(f"  Platform Details:   [bold]{platform.platform()}[/bold]")
            console.print(
                f"  Processor:          [bold]{platform.processor() or 'Unknown'}[/bold]"
            )

            # Memory and environment
            try:
                import psutil

                memory = psutil.virtual_memory()
                console.print(
                    f"  Memory (Total):     [bold]{memory.total / (1024**3):.1f} GB[/bold]"
                )
                console.print(
                    f"  Memory (Available): [bold]{memory.available / (1024**3):.1f} GB[/bold]"
                )
            except ImportError:
                console.print("  Memory Info:        [dim]psutil not available[/dim]")

            # Environment variables
            import os

            home_dir = os.path.expanduser("~")
            config_dir = Path(home_dir) / ".config" / "gerdsenai-cli"
            console.print(f"  Home Directory:     [bold]{home_dir}[/bold]")
            console.print(f"  Config Directory:   [bold]{config_dir}[/bold]")
            console.print(
                f"  Config Exists:      [bold]{'✅ Yes' if config_dir.exists() else '❌ No'}[/bold]"
            )

        # Component status
        console.print("\n🔧 [bold cyan]Component Status[/bold cyan]")

        # LLM Client
        llm_client = context.get("llm_client")
        if llm_client:
            try:
                health = await llm_client.health_check()
                status = (
                    "✅ Connected" if health.get("connected") else "❌ Disconnected"
                )
                console.print(f"  LLM Client:         [bold]{status}[/bold]")
                if health.get("server_url"):
                    console.print(
                        f"  Server URL:         [bold]{health['server_url']}[/bold]"
                    )
                if health.get("models_available"):
                    console.print(
                        f"  Models Available:   [bold]{health['models_available']}[/bold]"
                    )
                if health.get("error"):
                    console.print(
                        f"  Error:              [bold red]{health['error']}[/bold red]"
                    )
            except Exception as e:
                console.print(
                    f"  LLM Client:         [bold red]❌ Error: {str(e)}[/bold red]"
                )
        else:
            console.print(
                "  LLM Client:         [bold yellow]⚠️  Not initialized[/bold yellow]"
            )

        # Agent
        agent = context.get("agent")
        if agent:
            try:
                stats = agent.get_agent_stats()
                console.print("  AI Agent:           [bold green]✅ Ready[/bold green]")
                console.print(
                    f"  Files Indexed:      [bold]{stats.get('project_files_indexed', 0)}[/bold]"
                )
                console.print(
                    f"  Actions Performed:  [bold]{stats.get('actions_performed', 0)}[/bold]"
                )
            except Exception as e:
                console.print(
                    f"  AI Agent:           [bold red]❌ Error: {str(e)}[/bold red]"
                )
        else:
            console.print(
                "  AI Agent:           [bold yellow]⚠️  Not initialized[/bold yellow]"
            )

        # Command Parser
        parser = context.get("parser")
        if parser:
            try:
                parser_stats = parser.get_status()
                console.print("  Command Parser:     [bold green]✅ Ready[/bold green]")
                console.print(
                    f"  Commands Loaded:    [bold]{parser_stats.get('total_commands', 0)}[/bold]"
                )
                console.print(
                    f"  Aliases Available:  [bold]{parser_stats.get('total_aliases', 0)}[/bold]"
                )
            except Exception as e:
                console.print(
                    f"  Command Parser:     [bold red]❌ Error: {str(e)}[/bold red]"
                )
        else:
            console.print(
                "  Command Parser:     [bold yellow]⚠️  Not initialized[/bold yellow]"
            )

        # Installation path
        console.print("\n📦 [bold cyan]Installation Information[/bold cyan]")
        try:
            import gerdsenai_cli

            install_path = Path(gerdsenai_cli.__file__).parent
            console.print(f"  Installation Path:  [bold]{install_path}[/bold]")
            console.print(
                f"  Package Mode:       [bold]{'Development' if 'site-packages' not in str(install_path) else 'Installed'}[/bold]"
            )
        except Exception:
            console.print("  Installation Path:  [dim]Unable to determine[/dim]")

        # Troubleshooting tips
        console.print("\n💡 [bold cyan]Troubleshooting Tips[/bold cyan]")
        console.print("  • If LLM connection fails, check your server is running")
        console.print("  • Use '/setup' to reconfigure LLM server settings")
        console.print("  • Use '/status --verbose' for detailed component status")
        console.print("  • Check logs in ~/.config/gerdsenai-cli/logs/ if available")
        console.print(
            "  • Report issues at: https://github.com/GerdsenAI-Admin/GerdsenAI-CLI/issues"
        )

        console.print()
        return CommandResult(
            success=True,
            message="About information displayed",
            data={
                "version": __version__,
                "python_version": sys.version.split()[0],
                "platform": platform.system(),
                "detailed": detailed,
            },
        )


class InitCommand(BaseCommand):
    """Initialize project with GerdsenAI.md guide."""

    @property
    def name(self) -> str:
        return "init"

    @property
    def description(self) -> str:
        return "Initialize project with GerdsenAI.md guide and best practices"

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.SYSTEM

    @property
    def aliases(self) -> list[str]:
        return ["initialize", "setup-project"]

    def _define_arguments(self) -> dict[str, CommandArgument]:
        return {
            "force": CommandArgument(
                name="force",
                description="Overwrite existing GerdsenAI.md file if it exists",
                required=False,
                arg_type=bool,
                default=False,
            ),
            "template": CommandArgument(
                name="template",
                description="Project template type (python, web, general)",
                required=False,
                choices=["python", "web", "general"],
                default="general",
            ),
        }

    async def execute(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
        """Execute init command."""
        force = args.get("force", False)
        template = args.get("template", "general")

        # Check if GerdsenAI.md already exists
        guide_path = Path("GerdsenAI.md")
        if guide_path.exists() and not force:
            console.print(
                "[yellow]⚠️  GerdsenAI.md already exists in current directory.[/yellow]"
            )
            console.print(
                "[dim]Use --force to overwrite or choose a different directory.[/dim]\n"
            )
            return CommandResult(success=False, message="GerdsenAI.md already exists")

        # Generate content based on template
        content = self._generate_guide_content(template)

        try:
            # Write the guide file
            with open(guide_path, "w", encoding="utf-8") as f:
                f.write(content)

            console.print("[green]✅ Successfully created GerdsenAI.md![/green]")
            console.print(f"[dim]Location: {guide_path.absolute()}[/dim]\n")

            # Show quick tips
            self._show_quick_tips(template)

            return CommandResult(
                success=True,
                message="Project initialized with GerdsenAI.md",
                data={"guide_path": str(guide_path), "template": template},
            )

        except Exception as e:
            console.print(f"[red]❌ Failed to create GerdsenAI.md: {str(e)}[/red]\n")
            return CommandResult(
                success=False, message=f"Failed to create guide: {str(e)}"
            )

    def _generate_guide_content(self, template: str) -> str:
        """Generate guide content based on template."""

        base_content = """# GerdsenAI CLI - Project Guide

Welcome to your GerdsenAI-enabled project! This guide will help you work effectively with the AI coding assistant.

## 🚀 Getting Started

### Basic Commands
- **Chat with AI**: Just type your request naturally
- **Help**: `/help` - Show all available commands
- **Status**: `/status` - Check system and AI agent status
- **About**: `/about` - Version and troubleshooting info

### Essential File Operations
- **List files**: `/ls` or `/files` - Browse project structure
- **Read file**: `/cat <file>` or `/read <file>` - View file contents
- **Edit file**: `/edit <file> "description of changes"` - AI-assisted editing
- **Create file**: `/create <file> "description or content"` - Create new files
- **Search**: `/search <pattern>` - Find text across project files

### Project Context
- **Refresh context**: `/refresh` - Update AI's understanding of your project
- **Clear session**: `/clear` - Start fresh conversation
- **Agent status**: `/agent` - View AI agent statistics

## 💡 Best Practices

### Effective Communication
1. **Be specific**: Instead of "fix this", say "fix the login validation bug"
2. **Provide context**: Mention relevant files, functions, or requirements
3. **Ask questions**: "Why does this approach work better?" helps you learn
4. **Iterate**: Start with small changes, then build upon them

### Project Organization
- Keep your project structure clean and logical
- Use meaningful file and directory names
- Document important decisions in README or comments
- Regularly commit changes to version control

### Working with the AI
- **Explain your goals**: "I want to add user authentication to this web app"
- **Share constraints**: "Keep it compatible with Python 3.11+"
- **Request explanations**: "Explain how this algorithm works"
- **Ask for alternatives**: "What's another way to solve this?"

## 🔧 Advanced Features

### Session Management
- **Save session**: `/session save <name>` - Save current conversation
- **Load session**: `/session load <name>` - Restore previous session
- **List sessions**: `/session list` - View saved sessions

### Configuration
- **View config**: `/config` - Show current settings
- **Change model**: `/models` then `/model <name>` - Switch AI models
- **Setup**: `/setup` - Reconfigure LLM server connection

## 🎯 Common Workflows

### Starting a New Feature
1. Describe your goal: "I want to add a user profile page"
2. Ask for planning: "What files should I create/modify?"
3. Start implementation: "Create the user profile component"
4. Test and iterate: "Add error handling for missing user data"

### Debugging Issues
1. Describe the problem: "Users can't log in, getting 500 error"
2. Share relevant code: `/cat auth.py` or copy-paste snippets
3. Ask for analysis: "What could cause this error?"
4. Apply fixes: "/edit auth.py 'fix the password validation logic'"

### Code Review and Learning
1. Share your code: "Review this function for improvements"
2. Ask questions: "Is this the best way to handle errors?"
3. Learn patterns: "Show me examples of better error handling"
4. Apply improvements: Implement suggested changes

## 📋 Project-Specific Notes

> **Tip**: Use this section to document project-specific information:
> - Key architectural decisions
> - Important dependencies and their purposes
> - Deployment procedures
> - Team conventions and standards
> - Known issues or technical debt

## 🤝 Collaboration Tips

When working with team members:
- Share GerdsenAI session saves for complex problems
- Document AI-assisted solutions in commit messages
- Review AI-generated code just like human-written code
- Use the AI to explain complex code to team members

## 🔍 Troubleshooting

### Common Issues
- **AI not responding**: Check `/status` for connection issues
- **Slow responses**: Use `/refresh` to optimize context
- **Unexpected behavior**: Try `/clear` to reset session state
- **Connection errors**: Use `/setup` to reconfigure LLM server

### Getting Help
- Use `/about` to gather system information for bug reports
- Check the status with `/status --verbose` for detailed diagnostics
- Report issues at: https://github.com/GerdsenAI-Admin/GerdsenAI-CLI/issues

---

**Happy coding with GerdsenAI! 🚀**

*Last updated: {timestamp}*
"""

        # Template-specific additions
        template_additions = {
            "python": """

## 🐍 Python-Specific Tips

### Project Structure
```
your-project/
├── src/
│   └── your_package/
│       ├── __init__.py
│       ├── main.py
│       └── modules/
├── tests/
├── requirements.txt
├── pyproject.toml
├── README.md
└── GerdsenAI.md  # This file
```

### Common Python Tasks
- **Add dependencies**: "Add FastAPI and SQLAlchemy to requirements"
- **Create modules**: "Create a database connection module"
- **Write tests**: "Create unit tests for the user authentication"
- **Fix imports**: "Fix the import errors in this module"
- **Type hints**: "Add type hints to this function"

### Python Best Practices
- Use virtual environments (`python -m venv venv`)
- Follow PEP 8 style guidelines
- Write docstrings for functions and classes
- Use type hints for better code clarity
- Implement proper error handling
""",
            "web": """

## 🌐 Web Development Tips

### Typical Project Structure
```
your-web-project/
├── src/
│   ├── components/
│   ├── pages/
│   ├── styles/
│   └── utils/
├── public/
├── tests/
├── package.json
├── README.md
└── GerdsenAI.md  # This file
```

### Common Web Development Tasks
- **Create components**: "Create a responsive navigation component"
- **Add styling**: "Style this form with modern CSS"
- **Handle state**: "Add state management for user authentication"
- **API integration**: "Connect this component to the backend API"
- **Responsive design**: "Make this layout mobile-friendly"

### Web-Specific Best Practices
- Mobile-first responsive design
- Semantic HTML structure
- Efficient CSS organization
- Proper error handling for API calls
- Accessibility considerations (ARIA labels, keyboard navigation)
- Performance optimization (lazy loading, code splitting)
""",
            "general": """

## 📁 General Development Tips

### Effective Project Organization
- Group related files in directories
- Use consistent naming conventions
- Keep configuration files at project root
- Separate source code from documentation and tests

### Universal Best Practices
- Write clear, descriptive commit messages
- Document your decisions and reasoning
- Test your changes before committing
- Keep dependencies up to date
- Regular backups and version control
""",
        }

        # Add timestamp and template-specific content
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_content = base_content.format(
            timestamp=timestamp
        ) + template_additions.get(template, template_additions["general"])

        return full_content

    def _show_quick_tips(self, template: str):
        """Show quick tips after initialization."""
        console.print("[bold cyan]🎯 Quick Start Tips:[/bold cyan]")
        console.print("  1. Start chatting: Type your coding question or request")
        console.print("  2. Explore files: `/ls` to see project structure")
        console.print("  3. Get help: `/help` for all available commands")
        console.print("  4. Check status: `/status` to verify AI connection")

        if template == "python":
            console.print(
                "  5. Python-specific: Try 'Create a main.py with argument parsing'"
            )
        elif template == "web":
            console.print(
                "  5. Web-specific: Try 'Create an index.html with modern CSS'"
            )
        else:
            console.print("  5. Try this: 'Help me organize this project structure'")

        console.print(
            "\n[dim]💡 Read GerdsenAI.md for comprehensive guidance and best practices.[/dim]\n"
        )


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

    def _define_arguments(self) -> dict[str, CommandArgument]:
        return {
            "apply": CommandArgument(
                name="apply",
                description="Automatically apply defaults without prompts",
                required=False,
                arg_type=bool,
                default=False,
            )
        }

    async def execute(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
        from rich.prompt import Prompt

        settings = context.get("settings")
        config_manager = context.get("config_manager")
        if not settings or not config_manager:
            return CommandResult(
                success=False, message="Settings or config manager unavailable"
            )

        auto_apply = args.get("apply", False)

        try:
            if auto_apply:
                protocol = settings.protocol
                host = settings.llm_host
                port = settings.llm_port
            else:
                protocol = Prompt.ask(
                    "Protocol (http/https)",
                    choices=["http", "https"],
                    default=settings.protocol,
                )
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


class CopyCommand(BaseCommand):
    """Copy text or file contents to clipboard."""

    @property
    def name(self) -> str:
        return "copy"

    @property
    def description(self) -> str:
        return "Copy text or file contents to clipboard for sharing or external use"

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.SYSTEM

    @property
    def aliases(self) -> list[str]:
        return ["cp", "clip", "clipboard"]

    def _define_arguments(self) -> dict[str, CommandArgument]:
        return {
            "text": CommandArgument(
                name="text",
                description="Direct text to copy to clipboard",
                required=False,
            ),
            "file": CommandArgument(
                name="file",
                description="Path to file whose contents should be copied",
                required=False,
            ),
            "lines": CommandArgument(
                name="lines",
                description="Specific line range to copy (e.g., '1-10' or '5')",
                required=False,
            ),
            "format": CommandArgument(
                name="format",
                description="Output format for file contents",
                required=False,
                choices=["raw", "code", "markdown"],
                default="raw",
            ),
        }

    async def execute(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
        """Execute copy command."""
        text_arg = args.get("text")
        file_arg = args.get("file")
        lines_arg = args.get("lines")
        format_type = args.get("format", "raw")

        # Validate arguments
        if not text_arg and not file_arg:
            return CommandResult(
                success=False, message="Either --text or --file argument is required"
            )

        if text_arg and file_arg:
            return CommandResult(
                success=False,
                message="Cannot use both --text and --file arguments simultaneously",
            )

        try:
            # Determine what to copy
            if text_arg:
                content = text_arg
                source_info = "direct text"
            else:
                # Copy file contents
                if not file_arg:
                    return CommandResult(
                        success=False, message="File path is required"
                    )
                file_path = Path(file_arg)
                if not file_path.exists():
                    return CommandResult(
                        success=False, message=f"File not found: {file_arg}"
                    )

                if not file_path.is_file():
                    return CommandResult(
                        success=False, message=f"Path is not a file: {file_arg}"
                    )

                # Read file contents
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()
                    source_info = f"file: {file_arg}"
                except UnicodeDecodeError:
                    # Try binary files with basic encoding
                    try:
                        with open(file_path, encoding="latin1") as f:
                            content = f.read()
                        show_warning(
                            "File may contain binary data - using latin1 encoding"
                        )
                        source_info = f"file: {file_arg} (binary)"
                    except Exception as e:
                        return CommandResult(
                            success=False, message=f"Failed to read file: {str(e)}"
                        )
                except Exception as e:
                    return CommandResult(
                        success=False, message=f"Failed to read file: {str(e)}"
                    )

                # Handle line range selection
                if lines_arg:
                    content = self._extract_lines(content, lines_arg)
                    if content is None:
                        return CommandResult(
                            success=False, message=f"Invalid line range: {lines_arg}"
                        )

                # Apply formatting if requested and copying a file
                content = self._apply_formatting(
                    content, format_type, file_arg if file_arg else "text"
                )

            # Copy to clipboard
            success, error_msg = await self._copy_to_clipboard(content)

            if success:
                # Show success message with preview
                preview = content[:100] + "..." if len(content) > 100 else content
                preview_lines = preview.split("\n")
                if len(preview_lines) > 3:
                    preview = "\n".join(preview_lines[:3]) + "\n..."

                console.print("[green]✅ Copied to clipboard![/green]")
                console.print(f"[dim]Source: {source_info}[/dim]")
                console.print(f"[dim]Length: {len(content)} characters[/dim]")

                if len(content.split("\n")) > 1:
                    line_count = len(content.split("\n"))
                    console.print(f"[dim]Lines: {line_count}[/dim]")

                # Show preview
                console.print("\n[bold cyan]Preview:[/bold cyan]")
                console.print(Panel(preview, border_style="dim"))

                return CommandResult(
                    success=True,
                    message="Content copied to clipboard",
                    data={
                        "source": source_info,
                        "length": len(content),
                        "lines": len(content.split("\n")),
                        "format": format_type,
                    },
                )
            else:
                return CommandResult(
                    success=False, message=f"Failed to copy to clipboard: {error_msg}"
                )

        except Exception as e:
            return CommandResult(
                success=False, message=f"Copy operation failed: {str(e)}"
            )

    def _extract_lines(self, content: str, lines_spec: str) -> str | None:
        """Extract specific lines from content based on line specification.
        
        Returns:
            Extracted lines as string, or None if specification is invalid
        """
        lines = content.split("\n")
        total_lines = len(lines)

        try:
            if "-" in lines_spec:
                # Range specification (e.g., "5-10")
                start_str, end_str = lines_spec.split("-", 1)
                start_line = int(start_str.strip()) - 1  # Convert to 0-based index
                end_line = int(end_str.strip()) - 1  # Convert to 0-based index

                # Validate range
                if start_line < 0 or end_line >= total_lines or start_line > end_line:
                    return None

                return "\n".join(lines[start_line : end_line + 1])
            else:
                # Single line specification (e.g., "5")
                line_num = int(lines_spec.strip()) - 1  # Convert to 0-based index

                # Validate line number
                if line_num < 0 or line_num >= total_lines:
                    return None

                return lines[line_num]
        except (ValueError, IndexError):
            return None

    def _apply_formatting(self, content: str, format_type: str, source: str) -> str:
        """Apply formatting to content based on format type."""
        if format_type == "raw":
            return content
        elif format_type == "code":
            # Detect file extension for syntax highlighting hint
            if source != "text" and "." in source:
                ext = Path(source).suffix.lstrip(".")
                language_map = {
                    "py": "python",
                    "js": "javascript",
                    "ts": "typescript",
                    "html": "html",
                    "css": "css",
                    "json": "json",
                    "md": "markdown",
                    "sql": "sql",
                    "sh": "bash",
                    "yml": "yaml",
                    "yaml": "yaml",
                    "xml": "xml",
                }
                language = language_map.get(ext, ext)
                return f"```{language}\n{content}\n```"
            else:
                return f"```\n{content}\n```"
        elif format_type == "markdown":
            # Format as markdown with file info
            if source != "text":
                return f"**File:** `{source}`\n\n```\n{content}\n```"
            else:
                return f"```\n{content}\n```"

        return content

    async def _copy_to_clipboard(self, content: str) -> tuple[bool, str]:
        """Copy content to system clipboard with cross-platform support.
        
        Returns:
            Tuple of (success: bool, error_message: str). Empty string for success.
        """
        try:
            # Try to import and use pyperclip (most reliable cross-platform solution)
            try:
                import pyperclip

                pyperclip.copy(content)
                return True, ""
            except ImportError:
                # Fallback: use system commands
                return await self._system_clipboard_fallback(content)
            except Exception as e:
                # If pyperclip fails, try system fallback
                (
                    fallback_success,
                    fallback_error,
                ) = await self._system_clipboard_fallback(content)
                if fallback_success:
                    return True, ""
                else:
                    return (
                        False,
                        f"pyperclip failed ({str(e)}) and system fallback failed ({fallback_error})",
                    )

        except Exception as e:
            return False, str(e)

    async def _system_clipboard_fallback(self, content: str) -> tuple[bool, str]:
        """Fallback clipboard method using system commands."""
        import subprocess

        try:
            # Determine system and appropriate command
            system = platform.system().lower()

            if system == "darwin":  # macOS
                process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, text=True)
                process.communicate(input=content)
                return (
                    process.returncode == 0,
                    "" if process.returncode == 0 else "pbcopy failed",
                )

            elif system == "linux":
                # Try xclip first, then xsel
                try:
                    process = subprocess.Popen(
                        ["xclip", "-selection", "clipboard"],
                        stdin=subprocess.PIPE,
                        text=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    process.communicate(input=content)
                    if process.returncode == 0:
                        return True, ""
                except FileNotFoundError:
                    pass

                try:
                    process = subprocess.Popen(
                        ["xsel", "--clipboard", "--input"],
                        stdin=subprocess.PIPE,
                        text=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    process.communicate(input=content)
                    if process.returncode == 0:
                        return True, ""
                except FileNotFoundError:
                    pass

                return (
                    False,
                    "Neither xclip nor xsel found - install one of them for clipboard support",
                )

            elif system == "windows":
                process = subprocess.Popen(
                    ["clip"], stdin=subprocess.PIPE, text=True, shell=True
                )
                process.communicate(input=content)
                return (
                    process.returncode == 0,
                    "" if process.returncode == 0 else "clip.exe failed",
                )

            else:
                return False, f"Unsupported system: {system}"

        except Exception as e:
            return False, str(e)


class ToolsCommand(BaseCommand):
    """List available tools and capabilities in the CLI."""

    @property
    def name(self) -> str:
        return "tools"

    @property
    def description(self) -> str:
        return "List available tools and capabilities in GerdsenAI CLI"

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.SYSTEM

    @property
    def aliases(self) -> list[str]:
        return ["capabilities", "features"]

    def _define_arguments(self) -> dict[str, CommandArgument]:
        return {
            "category": CommandArgument(
                name="category",
                description="Filter by category (system, file, agent, model, terminal)",
                required=False,
                choices=["system", "file", "agent", "model", "terminal"],
            ),
            "detailed": CommandArgument(
                name="--detailed",
                description="Show detailed information about each tool",
                required=False,
                arg_type=bool,
                default=False,
            ),
            "search": CommandArgument(
                name="--search",
                description="Search tools by name or description",
                required=False,
            ),
        }

    async def execute(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
        """List available tools and capabilities."""
        category_filter = args.get("category")
        detailed = args.get("detailed", False)
        search_term = args.get("search")

        # Define tool categories and their descriptions
        tools = {
            "System Tools": {
                "category": "system",
                "description": "Core system operations and configuration",
                "tools": [
                    {
                        "name": "/help",
                        "description": "Show help for commands",
                        "aliases": ["/h", "/?"],
                        "usage": "/help [command]",
                    },
                    {
                        "name": "/status",
                        "description": "Show system and AI connection status",
                        "aliases": [],
                        "usage": "/status [--verbose]",
                    },
                    {
                        "name": "/about",
                        "description": "Show version and troubleshooting info",
                        "aliases": [],
                        "usage": "/about",
                    },
                    {
                        "name": "/config",
                        "description": "Display current configuration",
                        "aliases": [],
                        "usage": "/config",
                    },
                    {
                        "name": "/setup",
                        "description": "Interactive LLM server reconfiguration",
                        "aliases": [],
                        "usage": "/setup [--apply]",
                    },
                    {
                        "name": "/debug",
                        "description": "Toggle debug mode",
                        "aliases": [],
                        "usage": "/debug [on|off]",
                    },
                    {
                        "name": "/init",
                        "description": "Initialize project with GerdsenAI guide",
                        "aliases": [],
                        "usage": "/init [template]",
                    },
                    {
                        "name": "/copy",
                        "description": "Copy text or file contents to clipboard",
                        "aliases": ["/cp", "/clip"],
                        "usage": "/copy --text 'content' | --file path",
                    },
                    {
                        "name": "/exit",
                        "description": "Exit the application",
                        "aliases": ["/quit", "/q"],
                        "usage": "/exit",
                    },
                ],
            },
            "File Operations": {
                "category": "file",
                "description": "File and project management tools",
                "tools": [
                    {
                        "name": "/ls",
                        "description": "List files in project directory",
                        "aliases": ["/files", "/list"],
                        "usage": "/ls [path] [--detailed] [--filter pattern]",
                    },
                    {
                        "name": "/cat",
                        "description": "Read and display file contents",
                        "aliases": ["/read", "/view"],
                        "usage": "/cat <file> [--lines range] [--syntax]",
                    },
                    {
                        "name": "/edit",
                        "description": "AI-assisted file editing with preview",
                        "aliases": [],
                        "usage": "/edit <file> 'description of changes'",
                    },
                    {
                        "name": "/create",
                        "description": "Create new file with AI assistance",
                        "aliases": [],
                        "usage": "/create <file> 'description or content'",
                    },
                    {
                        "name": "/search",
                        "description": "Search text across project files",
                        "aliases": ["/find", "/grep"],
                        "usage": "/search <pattern> [--files] [--context]",
                    },
                    {
                        "name": "/session",
                        "description": "Manage conversation sessions",
                        "aliases": [],
                        "usage": "/session <save|load|list> [name]",
                    },
                ],
            },
            "AI Agent": {
                "category": "agent",
                "description": "AI assistant and context management",
                "tools": [
                    {
                        "name": "/agent",
                        "description": "Show AI agent statistics and status",
                        "aliases": [],
                        "usage": "/agent [--detailed]",
                    },
                    {
                        "name": "/chat",
                        "description": "Start or continue conversation with AI",
                        "aliases": ["/c"],
                        "usage": "/chat [message] | just type naturally",
                    },
                    {
                        "name": "/refresh",
                        "description": "Refresh project context for AI",
                        "aliases": [],
                        "usage": "/refresh",
                    },
                    {
                        "name": "/clear",
                        "description": "Clear conversation history",
                        "aliases": ["/reset"],
                        "usage": "/clear",
                    },
                ],
            },
            "Model Management": {
                "category": "model",
                "description": "LLM model selection and information",
                "tools": [
                    {
                        "name": "/models",
                        "description": "List available AI models",
                        "aliases": [],
                        "usage": "/models [--refresh]",
                    },
                    {
                        "name": "/model",
                        "description": "Switch to specific AI model",
                        "aliases": [],
                        "usage": "/model <name>",
                    },
                    {
                        "name": "/model-info",
                        "description": "Show detailed model information",
                        "aliases": [],
                        "usage": "/model-info [model_name]",
                    },
                    {
                        "name": "/model-stats",
                        "description": "Show model usage statistics",
                        "aliases": [],
                        "usage": "/model-stats",
                    },
                ],
            },
            "Terminal Integration": {
                "category": "terminal",
                "description": "Safe terminal command execution",
                "tools": [
                    {
                        "name": "/run",
                        "description": "Execute terminal commands safely",
                        "aliases": ["/exec"],
                        "usage": "/run <command> [--confirm]",
                    },
                    {
                        "name": "/pwd",
                        "description": "Show current working directory",
                        "aliases": [],
                        "usage": "/pwd",
                    },
                    {
                        "name": "/history",
                        "description": "Show command execution history",
                        "aliases": [],
                        "usage": "/history [--limit n]",
                    },
                    {
                        "name": "/clear-history",
                        "description": "Clear command execution history",
                        "aliases": [],
                        "usage": "/clear-history",
                    },
                    {
                        "name": "/terminal-status",
                        "description": "Show terminal integration status",
                        "aliases": [],
                        "usage": "/terminal-status",
                    },
                ],
            },
        }

        # Apply filters
        filtered_tools = {}
        for category_name, category_data in tools.items():
            if category_filter and category_data["category"] != category_filter:
                continue

            category_tools = category_data["tools"]
            if search_term:
                search_lower = search_term.lower()
                category_tools = [
                    tool
                    for tool in category_tools
                    if search_lower in tool["name"].lower()
                    or search_lower in tool["description"].lower()
                    or any(search_lower in alias.lower() for alias in tool["aliases"])
                ]

            if category_tools:  # Only include categories with matching tools
                filtered_tools[category_name] = {
                    **category_data,
                    "tools": category_tools,
                }

        # Display results
        if not filtered_tools:
            message = "No tools found"
            if category_filter:
                message += f" in category '{category_filter}'"
            if search_term:
                message += f" matching '{search_term}'"
            console.print(f"[yellow]{message}[/yellow]")
            return CommandResult(success=True, message=message)

        # Show header
        console.print("[bold cyan]🔧 GerdsenAI CLI Tools & Capabilities[/bold cyan]")
        if category_filter:
            console.print(f"[dim]Filtered by category: {category_filter}[/dim]")
        if search_term:
            console.print(f"[dim]Search term: {search_term}[/dim]")
        console.print()

        # Display each category
        for category_name, category_data in filtered_tools.items():
            console.print(f"[bold]{category_name}[/bold]")
            console.print(f"[dim]{category_data['description']}[/dim]")
            console.print()

            for tool in category_data["tools"]:
                # Tool name and description
                console.print(
                    f"  [green]{tool['name']}[/green] - {tool['description']}"
                )

                if detailed:
                    # Show aliases if any
                    if tool["aliases"]:
                        aliases_str = ", ".join(tool["aliases"])
                        console.print(f"    [dim]Aliases: {aliases_str}[/dim]")

                    # Show usage
                    console.print(f"    [dim]Usage: {tool['usage']}[/dim]")

                    console.print()  # Extra spacing in detailed mode

            console.print()  # Category separator

        # Show summary
        total_tools = sum(len(cat["tools"]) for cat in filtered_tools.values())
        console.print(f"[dim]Total tools shown: {total_tools}[/dim]")

        if not detailed:
            console.print(
                "[dim]💡 Use --detailed for more information about each tool[/dim]"
            )

        return CommandResult(
            success=True,
            message=f"Listed {total_tools} tools",
            data={
                "categories": len(filtered_tools),
                "tools": total_tools,
                "filtered": bool(category_filter or search_term),
            },
        )


class TuiCommand(BaseCommand):
    """Toggle enhanced TUI mode."""

    @property
    def name(self) -> str:
        return "tui"

    @property
    def description(self) -> str:
        return "Toggle enhanced TUI mode (Text User Interface)"

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.SYSTEM

    @property
    def aliases(self) -> list[str]:
        return ["ui"]

    def _define_arguments(self) -> dict[str, CommandArgument]:
        return {
            "mode": CommandArgument(
                name="mode",
                description="TUI mode: 'on', 'off', or 'toggle' (default)",
                required=False,
            )
        }

    async def execute(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
        """Execute TUI toggle command."""
        settings = context.get("settings")
        config_manager = context.get("config_manager")

        if not settings or not config_manager:
            return CommandResult(
                success=False, message="Settings or config manager not available"
            )

        mode = args.get("mode", "toggle").lower()

        # Get current TUI mode
        current_mode = settings.user_preferences.get("tui_mode", True)

        # Determine new mode
        if mode == "on":
            new_mode = True
        elif mode == "off":
            new_mode = False
        elif mode == "toggle":
            new_mode = not current_mode
        else:
            return CommandResult(
                success=False, message=f"Invalid mode: {mode}. Use 'on', 'off', or 'toggle'"
            )

        # Update settings
        settings.user_preferences["tui_mode"] = new_mode

        # Save settings
        save_success = await config_manager.save_settings(settings)

        if not save_success:
            return CommandResult(
                success=False, message="Failed to save TUI preference to settings"
            )

        # Show result
        status = "enabled" if new_mode else "disabled"
        icon = "✨" if new_mode else "📝"

        show_success(f"{icon} Enhanced TUI mode {status}")

        if new_mode:
            show_info("TUI features: syntax highlighting, status bar, 3-panel layout")
        else:
            show_info("Using simple console output mode")

        return CommandResult(
            success=True,
            message=f"TUI mode {status}",
            data={"tui_mode": new_mode},
        )
