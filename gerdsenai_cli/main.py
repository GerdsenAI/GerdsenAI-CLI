"""
Main application class for GerdsenAI CLI.

This module contains the core application logic and interactive loop.
"""

import asyncio
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.prompt import Prompt
from rich.text import Text

from .config.manager import ConfigManager
from .config.settings import Settings
from .core.llm_client import LLMClient, ChatMessage
from .core.agent import Agent
from .utils.display import show_error, show_info, show_success, show_warning, show_startup_sequence

# Import command system
from .commands.parser import CommandParser
from .commands.system import HelpCommand, ExitCommand, StatusCommand, ConfigCommand, DebugCommand, SetupCommand, AboutCommand, InitCommand, CopyCommand
from .commands.model import ListModelsCommand, SwitchModelCommand, ModelInfoCommand, ModelStatsCommand
from .commands.agent import AgentStatusCommand, ConversationCommand, RefreshContextCommand, ClearSessionCommand, AgentConfigCommand
from .commands.files import ListFilesCommand, ReadFileCommand, EditFileCommand, CreateFileCommand, SearchFilesCommand, SessionCommand
from .commands.terminal import RunCommand, HistoryCommand, ClearHistoryCommand, WorkingDirectoryCommand, TerminalStatusCommand

console = Console()


class GerdsenAICLI:
    """Main GerdsenAI CLI application class."""
    
    def __init__(self, config_path: Optional[str] = None, debug: bool = False):
        """
        Initialize the GerdsenAI CLI.
        
        Args:
            config_path: Optional path to configuration file
            debug: Enable debug mode
        """
        self.debug = debug
        self.config_manager = ConfigManager(config_path)
        self.settings: Optional[Settings] = None
        self.running = False
        
        # Initialize components
        self.llm_client: Optional[LLMClient] = None
        self.agent: Optional[Agent] = None
        self.command_parser: Optional[CommandParser] = None
        
    async def initialize(self) -> bool:
        """
        Initialize the application components.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load or create configuration
            self.settings = await self.config_manager.load_settings()
            
            if not self.settings:
                show_info("First time setup detected. Let's configure your local AI server.")
                self.settings = await self._first_time_setup()
                if not self.settings:
                    show_error("Setup cancelled or failed.")
                    return False
            
            # Initialize LLM client
            self.llm_client = LLMClient(self.settings)
            
            # Test connection to LLM server
            show_info("Testing connection to LLM server...")
            connected = await self.llm_client.connect()
            
            if not connected:
                show_warning("Could not connect to LLM server. Please check your configuration.")
                return False
            
            # Load available models
            models = await self.llm_client.list_models()
            if not models:
                show_warning("No models found on the LLM server.")
            else:
                show_info(f"Found {len(models)} available models")
                
                # Set current model if not already set
                if not self.settings.current_model and models:
                    self.settings.current_model = models[0].id
                    await self.config_manager.save_settings(self.settings)
                    show_info(f"Set default model to: {models[0].id}")
            
            # Initialize AI agent with agentic capabilities
            self.agent = Agent(self.llm_client, self.settings)
            agent_ready = await self.agent.initialize()
            
            if not agent_ready:
                show_warning("Agent initialization failed, some features may be limited")
            
            # Initialize command system
            await self._initialize_commands()
            
            show_success("GerdsenAI CLI initialized successfully!")
            return True
            
        except Exception as e:
            show_error(f"Failed to initialize: {e}")
            if self.debug:
                console.print_exception()
            return False
    
    async def _initialize_commands(self) -> None:
        """Initialize the command parser and register all commands."""
        self.command_parser = CommandParser()
        
        # Create command dependencies
        command_deps = {
            'llm_client': self.llm_client,
            'agent': self.agent,
            'settings': self.settings,
            'config_manager': self.config_manager,
            'console': console
        }
        
        # Register system commands
        await self.command_parser.register_command(HelpCommand(**command_deps))
        await self.command_parser.register_command(ExitCommand(**command_deps))
        await self.command_parser.register_command(StatusCommand(**command_deps))
        await self.command_parser.register_command(ConfigCommand(**command_deps))
        await self.command_parser.register_command(DebugCommand(**command_deps))
        await self.command_parser.register_command(SetupCommand(**command_deps))
        
        # Register Phase 5.5 Essential Commands
        await self.command_parser.register_command(AboutCommand(**command_deps))
        await self.command_parser.register_command(InitCommand(**command_deps))
        await self.command_parser.register_command(CopyCommand(**command_deps))
        
        # Register model commands
        await self.command_parser.register_command(ListModelsCommand(**command_deps))
        await self.command_parser.register_command(SwitchModelCommand(**command_deps))
        await self.command_parser.register_command(ModelInfoCommand(**command_deps))
        await self.command_parser.register_command(ModelStatsCommand(**command_deps))
        
        # Register agent commands
        await self.command_parser.register_command(AgentStatusCommand(**command_deps))
        await self.command_parser.register_command(ConversationCommand(**command_deps))
        await self.command_parser.register_command(RefreshContextCommand(**command_deps))
        await self.command_parser.register_command(ClearSessionCommand(**command_deps))
        await self.command_parser.register_command(AgentConfigCommand(**command_deps))
        
        # Register file commands
        await self.command_parser.register_command(ListFilesCommand(**command_deps))
        await self.command_parser.register_command(ReadFileCommand(**command_deps))
        await self.command_parser.register_command(EditFileCommand(**command_deps))
        await self.command_parser.register_command(CreateFileCommand(**command_deps))
        await self.command_parser.register_command(SearchFilesCommand(**command_deps))
        await self.command_parser.register_command(SessionCommand(**command_deps))
        
        # Register terminal commands (Phase 6)
        await self.command_parser.register_command(RunCommand(**command_deps))
        await self.command_parser.register_command(HistoryCommand(**command_deps))
        await self.command_parser.register_command(ClearHistoryCommand(**command_deps))
        await self.command_parser.register_command(WorkingDirectoryCommand(**command_deps))
        await self.command_parser.register_command(TerminalStatusCommand(**command_deps))

    async def _first_time_setup(self) -> Optional[Settings]:
        """
        Handle first-time setup process.
        
        Returns:
            Settings object if setup successful, None otherwise
        """
        try:
            console.print("\n[SETUP] [bold cyan]GerdsenAI CLI Setup[/bold cyan]\n")
            
            # Gather granular server configuration
            protocol = Prompt.ask(
                "Protocol (http/https)",
                choices=["http", "https"],
                default="http",
                console=console
            )
            host = Prompt.ask(
                "LLM server host or IP",
                default="localhost",
                console=console
            )
            port_str = Prompt.ask(
                "Port",
                default="11434",
                console=console
            )
            try:
                port = int(port_str)
            except ValueError:
                show_warning("Invalid port provided, falling back to 11434")
                port = 11434

            llm_url = f"{protocol}://{host}:{port}"

            # Test connection to LLM server
            show_info("Testing connection to LLM server...")
            
            temp_client = LLMClient(Settings(protocol=protocol, llm_host=host, llm_port=port))
            connected = await temp_client.connect()
            
            if not connected:
                show_error("Could not connect to the LLM server. Please check the URL and try again.")
                await temp_client.close()
                return None
            
            # Get available models
            models = await temp_client.list_models()
            await temp_client.close()
            
            default_model = ""
            if models:
                show_success(f"Connected! Found {len(models)} available models:")
                for i, model in enumerate(models[:5]):  # Show first 5 models
                    console.print(f"  {i+1}. {model.id}")
                
                if len(models) > 5:
                    console.print(f"  ... and {len(models) - 5} more")
                
                # Let user select default model
                if len(models) == 1:
                    default_model = models[0].id
                    show_info(f"Using model: {default_model}")
                else:
                    model_choice = Prompt.ask(
                        "Select default model",
                        choices=[str(i+1) for i in range(len(models))],
                        default="1"
                    )
                    default_model = models[int(model_choice) - 1].id
                    show_info(f"Selected model: {default_model}")
            else:
                show_warning("No models found, but connection successful.")
            
            settings = Settings(
                protocol=protocol,
                llm_host=host,
                llm_port=port,
                current_model=default_model,
                api_timeout=30.0,
                user_preferences={
                    "theme": "dark",
                    "show_timestamps": True,
                    "auto_save": True
                }
            )
            
            # Save settings
            success = await self.config_manager.save_settings(settings)
            if success:
                show_success("Configuration saved successfully!")
                return settings
            else:
                show_error("Failed to save configuration.")
                return None
                
        except KeyboardInterrupt:
            show_warning("Setup cancelled by user.")
            return None
        except Exception as e:
            show_error(f"Setup failed: {e}")
            if self.debug:
                console.print_exception()
            return None
    
    def _create_prompt(self) -> Text:
        """
        Create the interactive prompt text.
        
        Returns:
            Rich Text object for the prompt
        """
        prompt_text = Text()
        prompt_text.append("[AI] ", style="bright_cyan")
        prompt_text.append("GerdsenAI", style="bold bright_cyan")
        prompt_text.append(" > ", style="white")
        return prompt_text
    
    async def _handle_user_input(self, user_input: str) -> bool:
        """
        Handle user input and route to appropriate handler.
        
        Args:
            user_input: The user's input string
            
        Returns:
            True to continue running, False to exit
        """
        if not user_input.strip():
            return True
            
        # Handle slash commands
        if user_input.startswith('/'):
            return await self._handle_command(user_input)
        
        # Handle regular chat input
        return await self._handle_chat(user_input)
    
    async def _handle_command(self, command: str) -> bool:
        """
        Handle slash commands using the command parser.

        Args:
            command: The command string starting with '/'

        Returns:
            True to continue running, False to exit
        """
        if not self.command_parser:
            show_error("Command parser not initialized")
            return True
        
        try:
            # Parse and execute the command
            result = await self.command_parser.parse_and_execute(command)
            
            # Handle exit command result
            if result and result.get('exit', False):
                return False
                
            return True
            
        except Exception as e:
            show_error(f"Command error: {e}")
            if self.debug:
                console.print_exception()
            return True
    
    async def _handle_chat(self, message: str) -> bool:
        """
        Handle chat messages (non-command input).

        Args:
            message: The chat message

        Returns:
            True to continue running, False to exit
        """
        if not self.agent:
            show_error("AI agent not initialized")
            return True

        try:
            # Use the agent to process user input with full agentic capabilities
            response = await self.agent.process_user_input(message)

            if response:
                console.print("\n[AI] [bold cyan]GerdsenAI[/bold cyan]:")
                console.print(response)
                console.print()
            else:
                show_error("Failed to get response from AI agent")

        except Exception as e:
            show_error(f"Agent error: {e}")
            if self.debug:
                console.print_exception()

        return True
    

    async def run_async(self) -> None:
        """Run the async main loop."""
        # Show startup sequence with ASCII art
        show_startup_sequence()
        
        # Initialize the application
        if not await self.initialize():
            return

        self.running = True

        try:
            while self.running:
                # Create and display prompt
                prompt_text = self._create_prompt()

                # Get user input
                user_input = Prompt.ask(prompt_text, console=console)

                # Handle the input
                continue_running = await self._handle_user_input(user_input)
                if not continue_running:
                    self.running = False

        except KeyboardInterrupt:
            console.print("\n[INFO] Goodbye!", style="bright_cyan")
        except Exception as e:
            show_error(f"An error occurred: {e}")
            if self.debug:
                console.print_exception()
        finally:
            # Clean up resources
            if self.llm_client:
                await self.llm_client.close()
    
    def run(self) -> None:
        """Run the main application loop."""
        try:
            asyncio.run(self.run_async())
        except Exception as e:
            show_error(f"Failed to start application: {e}")
            if self.debug:
                console.print_exception()
