"""
Main application class for GerdsenAI CLI.

This module contains the core application logic and interactive loop.
"""

import asyncio

from rich.console import Console
from rich.prompt import Prompt

from .commands.agent import (
    AgentConfigCommand,
    AgentStatusCommand,
    ChatCommand,
    RefreshContextCommand,
    ResetCommand,
)
from .commands.files import (
    CreateFileCommand,
    EditFileCommand,
    FilesCommand,
    ReadCommand,
    SearchFilesCommand,
    SessionCommand,
)
from .commands.model import (
    ListModelsCommand,
    ModelInfoCommand,
    ModelStatsCommand,
    SwitchModelCommand,
)

# Import command system
from .commands.parser import CommandParser
from .commands.system import (
    AboutCommand,
    ConfigCommand,
    CopyCommand,
    DebugCommand,
    ExitCommand,
    HelpCommand,
    InitCommand,
    SetupCommand,
    StatusCommand,
    ToolsCommand,
    TuiCommand,
)
from .commands.terminal import (
    ClearHistoryCommand,
    HistoryCommand,
    RunCommand,
    TerminalStatusCommand,
    WorkingDirectoryCommand,
)
from .config.manager import ConfigManager
from .config.settings import Settings
from .core.agent import Agent
from .core.llm_client import LLMClient
from .ui.console import EnhancedConsole
from .ui.input_handler import EnhancedInputHandler
from .utils.display import (
    show_error,
    show_info,
    show_startup_sequence,
    show_success,
    show_warning,
)

console = Console()


class GerdsenAICLI:
    """Main GerdsenAI CLI application class."""

    def __init__(self, config_path: str | None = None, debug: bool = False):
        """
        Initialize the GerdsenAI CLI.

        Args:
            config_path: Optional path to configuration file
            debug: Enable debug mode
        """
        self.debug = debug
        self.config_manager = ConfigManager(config_path)
        self.settings: Settings | None = None
        self.running = False

        # Initialize components
        self.llm_client: LLMClient | None = None
        self.agent: Agent | None = None
        self.command_parser: CommandParser | None = None
        self.input_handler: EnhancedInputHandler | None = None
        self.enhanced_console: EnhancedConsole | None = None

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
                show_info(
                    "First time setup detected. Let's configure your local AI server."
                )
                self.settings = await self._first_time_setup()
                if not self.settings:
                    show_error("Setup cancelled or failed.")
                    return False

            # Initialize LLM client with async context manager
            self.llm_client = LLMClient(self.settings)
            await self.llm_client.__aenter__()  # Enter async context

            # Test connection to LLM server
            show_info("Testing connection to LLM server...")
            connected = await self.llm_client.connect()

            if not connected:
                show_warning(
                    "Could not connect to LLM server. Please check your configuration."
                )
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

            # Initialize enhanced console with TUI first
            self.enhanced_console = EnhancedConsole(console)
            
            # Initialize AI agent with agentic capabilities (pass console for intelligence display)
            self.agent = Agent(
                self.llm_client,
                self.settings,
                console=self.enhanced_console
            )
            agent_ready = await self.agent.initialize()

            if not agent_ready:
                show_warning(
                    "Agent initialization failed, some features may be limited"
                )

            # Initialize command system
            await self._initialize_commands()

            # Initialize enhanced input handler
            self.input_handler = EnhancedInputHandler(
                command_parser=self.command_parser
            )
            
            # Update status bar with initial info
            context_files = len(self.agent.context_manager.files) if self.agent and hasattr(self.agent, 'context_manager') else 0
            self.enhanced_console.update_status(
                model=self.settings.current_model,
                context_files=context_files,
                token_count=0
            )

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

        # Set execution context for commands (passed to execute() method)
        command_context = {
            "llm_client": self.llm_client,
            "agent": self.agent,
            "settings": self.settings,
            "config_manager": self.config_manager,
            "console": console,
        }
        self.command_parser.set_context(command_context)

        # Register system commands
        self.command_parser.register_command(HelpCommand())
        self.command_parser.register_command(ExitCommand())
        self.command_parser.register_command(StatusCommand())
        self.command_parser.register_command(ConfigCommand())
        self.command_parser.register_command(DebugCommand())
        self.command_parser.register_command(SetupCommand())
        self.command_parser.register_command(AboutCommand())
        self.command_parser.register_command(CopyCommand())
        self.command_parser.register_command(InitCommand())
        self.command_parser.register_command(ToolsCommand())
        self.command_parser.register_command(TuiCommand())

        # Register model commands
        self.command_parser.register_command(ListModelsCommand())
        self.command_parser.register_command(SwitchModelCommand())
        self.command_parser.register_command(ModelInfoCommand())
        self.command_parser.register_command(ModelStatsCommand())

        # Register agent commands
        self.command_parser.register_command(AgentStatusCommand())
        self.command_parser.register_command(ChatCommand())
        self.command_parser.register_command(RefreshContextCommand())
        self.command_parser.register_command(ResetCommand())
        self.command_parser.register_command(AgentConfigCommand())

        # Register file commands
        self.command_parser.register_command(FilesCommand())
        self.command_parser.register_command(ReadCommand())
        self.command_parser.register_command(EditFileCommand())
        self.command_parser.register_command(CreateFileCommand())
        self.command_parser.register_command(SearchFilesCommand())
        self.command_parser.register_command(SessionCommand())

        # Register terminal commands (Phase 6)
        self.command_parser.register_command(RunCommand())
        self.command_parser.register_command(HistoryCommand())
        self.command_parser.register_command(ClearHistoryCommand())
        self.command_parser.register_command(WorkingDirectoryCommand())
        self.command_parser.register_command(TerminalStatusCommand())

    async def _first_time_setup(self) -> Settings | None:
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
                console=console,
            )
            host = Prompt.ask(
                "LLM server host or IP", default="127.0.0.1", console=console
            )
            port_str = Prompt.ask("Port", default="11434", console=console)
            try:
                port = int(port_str)
            except ValueError:
                show_warning("Invalid port provided, falling back to 11434")
                port = 11434

            # Test connection to LLM server with timeout
            show_info("Testing connection to LLM server...")

            temp_settings = Settings(protocol=protocol, llm_host=host, llm_port=port)

            try:
                # Use async context manager for proper client lifecycle
                async with LLMClient(temp_settings) as temp_client:
                    # Wrap the entire connection test in a timeout to prevent hanging
                    print(f"[DEBUG] Attempting connection to {protocol}://{host}:{port}")
                    connected = await asyncio.wait_for(
                        temp_client.connect(),
                        timeout=15.0,  # 15 second total timeout for setup
                    )
                    print(f"[DEBUG] Connection result: {connected}")

                    if not connected:
                        show_error(
                            "Could not connect to the LLM server. Please check the URL and try again."
                        )
                        return None

                    # Get available models
                    models = await temp_client.list_models()
            except asyncio.TimeoutError:
                print("[DEBUG] Connection test timed out after 15 seconds")
                show_error(
                    "Connection test timed out. Please check if your LLM server is running and accessible."
                )
                return None
            except Exception as e:
                print(f"[DEBUG] Connection test failed with exception: {e}")
                show_error(f"Connection test failed: {e}")
                return None

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
                        choices=[str(i + 1) for i in range(len(models))],
                        default="1",
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
                    "auto_save": True,
                },
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
        if user_input.startswith("/"):
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
            result = await self.command_parser.execute_command(command)

            # Handle exit command result
            if result.should_exit:
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
            # Check if TUI mode and streaming are enabled in preferences
            tui_mode = self.settings.user_preferences.get("tui_mode", True) if self.settings else True
            streaming_enabled = self.settings.user_preferences.get("streaming", True) if self.settings else True
            
            if streaming_enabled:
                # Use streaming for real-time response
                if tui_mode and self.enhanced_console:
                    # Start streaming with enhanced console
                    self.enhanced_console.start_streaming(message)
                    
                    # Set initial status: thinking
                    self.enhanced_console.set_operation("thinking")
                    
                    # Create status callback for agent
                    def update_operation(operation: str) -> None:
                        if self.enhanced_console:
                            self.enhanced_console.set_operation(operation)
                    
                    accumulated_response = ""
                    chunk_count = 0
                    async for chunk, full_response in self.agent.process_user_input_stream(
                        message, status_callback=update_operation
                    ):
                        accumulated_response = full_response
                        chunk_count += 1
                        
                        # Update operation status based on progress
                        if chunk_count == 1:
                            # First chunk arrived - we're now streaming
                            self.enhanced_console.set_operation("streaming")
                        
                        self.enhanced_console.stream_chunk(chunk, accumulated_response)
                    
                    # Mark as complete
                    self.enhanced_console.set_operation("synthesizing")
                    self.enhanced_console.finish_streaming()
                else:
                    # Fallback to simple streaming
                    console.print(f"\n[bold green]You:[/bold green] {message}")
                    console.print("[bold cyan]GerdsenAI:[/bold cyan]", end=" ")
                    
                    accumulated_response = ""
                    async for chunk, full_response in self.agent.process_user_input_stream(message):
                        accumulated_response = full_response
                        console.print(chunk, end="", style="white")
                    
                    console.print()  # Final newline
            else:
                # Non-streaming mode
                response = await self.agent.process_user_input(message)

                if response:
                    # Use enhanced console for rich formatting and syntax highlighting
                    if tui_mode and self.enhanced_console:
                        self.enhanced_console.print_message(
                            user_input=message,
                            ai_response=response
                        )
                    else:
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
                try:
                    # Get user input using enhanced input handler
                    if not self.input_handler:
                        show_error("Input handler not initialized")
                        break

                    user_input = await self.input_handler.get_user_input()

                    # Handle the input
                    continue_running = await self._handle_user_input(user_input)
                    if not continue_running:
                        self.running = False

                except KeyboardInterrupt:
                    # User pressed Ctrl+C during input
                    continue
                except EOFError:
                    # User pressed Ctrl+D (exit signal)
                    console.print("\n[INFO] Goodbye!", style="bright_cyan")
                    self.running = False

        except KeyboardInterrupt:
            console.print("\n[INFO] Goodbye!", style="bright_cyan")
        except Exception as e:
            show_error(f"An error occurred: {e}")
            if self.debug:
                console.print_exception()
        finally:
            # Clean up resources
            if self.agent:
                await self.agent.cleanup()
            if self.input_handler:
                await self.input_handler.cleanup()
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
