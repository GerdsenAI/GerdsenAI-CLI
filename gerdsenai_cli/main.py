"""
Main application class for GerdsenAI CLI.

This module contains the core application logic and interactive loop.
"""

import asyncio
import logging
from datetime import datetime

from rich.console import Console
from rich.prompt import Prompt

logger = logging.getLogger(__name__)

from rich.console import Console
from rich.prompt import Prompt

logger = logging.getLogger(__name__)

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
from .commands.intelligence import IntelligenceCommand
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
from .utils.conversation_io import ConversationManager
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
        self.conversation_manager = ConversationManager()

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
        if self.agent:
            self.command_parser.register_command(
                IntelligenceCommand(self.agent, self.enhanced_console)
            )

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
        
        # Check if TUI mode is enabled
        tui_mode = self.settings.user_preferences.get("tui_mode", True) if self.settings else True
        persistent_mode = self.settings.user_preferences.get("persistent_tui", True) if self.settings else True

        try:
            # Use persistent TUI mode if enabled
            if tui_mode and persistent_mode and self.enhanced_console:
                await self._run_persistent_tui_mode()
            else:
                # Fall back to original input handler mode
                await self._run_standard_mode()

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
    
    async def _handle_tui_command(self, command: str, args: list[str], tui=None) -> str:
        """Handle TUI commands like /model, /save, /load, /export.
        
        Args:
            command: The command string (e.g., '/model')
            args: List of command arguments
            tui: Optional TUI instance for accessing conversation data
            
        Returns:
            Response string to display to user
        """
        try:
            if command == '/model':
                if not args:
                    # Show current model
                    current = self.settings.current_model if self.settings and self.settings.current_model else "not set"
                    return f"Current model: {current}\n\nUse '/model <name>' to switch models."
                else:
                    # Switch to new model
                    new_model = args[0]
                    if self.settings:
                        self.settings.current_model = new_model
                        if self.agent and hasattr(self.agent, 'settings'):
                            self.agent.settings.current_model = new_model
                        
                        # Update TUI footer if TUI is available
                        if tui:
                            tui.set_system_footer(f"Model: {new_model}")
                        
                        return f"Switched to model: {new_model}"
                    else:
                        return "Error: Settings not initialized"
            
            elif command == '/save':
                if not args:
                    return "Usage: /save <filename>\n\nExample: /save my_conversation"
                
                if not tui:
                    return "Error: TUI not available for save operation"
                
                filename = args[0]
                
                # Get conversation messages from TUI
                messages = tui.conversation.messages
                
                if not messages:
                    return "No messages to save. Start a conversation first."
                
                # Prepare metadata
                metadata = {
                    "model": self.settings.current_model if self.settings else "unknown",
                    "message_count": len(messages),
                }
                
                # Save conversation
                try:
                    filepath = self.conversation_manager.save_conversation(filename, messages, metadata)
                    return f"Conversation saved successfully!\n\nFile: {filepath}\nMessages: {len(messages)}"
                except Exception as e:
                    logger.error(f"Error saving conversation: {e}", exc_info=True)
                    return f"Error saving conversation: {str(e)}"
            
            elif command == '/load':
                if not args:
                    # List available conversations
                    conversations = self.conversation_manager.list_conversations()
                    if not conversations:
                        return "No saved conversations found.\n\nUse '/save <filename>' to save a conversation."
                    
                    lines = ["Available conversations:", ""]
                    for conv_file in conversations:
                        lines.append(f"  - {conv_file.stem}")
                    lines.append("")
                    lines.append("Use '/load <filename>' to load a conversation.")
                    return "\n".join(lines)
                
                if not tui:
                    return "Error: TUI not available for load operation"
                
                filename = args[0]
                
                # Load conversation
                try:
                    messages, metadata = self.conversation_manager.load_conversation(filename)
                    
                    # Clear current conversation
                    tui.conversation.clear_messages()
                    
                    # Load messages into TUI
                    for role, content, _ in messages:
                        tui.conversation.add_message(role, content)
                    
                    # Build response
                    msg_count = len(messages)
                    lines = [
                        f"Conversation loaded successfully!",
                        f"\nFile: {filename}",
                        f"Messages: {msg_count}",
                    ]
                    
                    if metadata:
                        lines.append("\nMetadata:")
                        for key, value in metadata.items():
                            lines.append(f"  {key}: {value}")
                    
                    return "\n".join(lines)
                    
                except FileNotFoundError:
                    return f"Conversation not found: {filename}\n\nUse '/load' without arguments to list available conversations."
                except Exception as e:
                    logger.error(f"Error loading conversation: {e}", exc_info=True)
                    return f"Error loading conversation: {str(e)}"
            
            elif command == '/export':
                if not tui:
                    return "Error: TUI not available for export operation"
                
                # Get conversation messages from TUI
                messages = tui.conversation.messages
                
                if not messages:
                    return "No messages to export. Start a conversation first."
                
                filename = args[0] if args else None
                
                # Prepare metadata
                metadata = {
                    "model": self.settings.current_model if self.settings else "unknown",
                    "message_count": len(messages),
                    "exported_at": datetime.now().isoformat(),
                }
                
                # Export conversation
                try:
                    filepath = self.conversation_manager.export_conversation(filename, messages, metadata)
                    return f"Conversation exported successfully!\n\nFile: {filepath}\nFormat: Markdown\nMessages: {len(messages)}"
                except Exception as e:
                    logger.error(f"Error exporting conversation: {e}", exc_info=True)
                    return f"Error exporting conversation: {str(e)}"
            
            return f"Unknown command: {command}"
            
        except Exception as e:
            logger.error(f"Command handler error: {e}", exc_info=True)
            return f"Command error: {str(e)}"

    async def _run_persistent_tui_mode(self) -> None:
        """Run in persistent TUI mode with embedded input using prompt_toolkit."""
        import logging
        from .ui.prompt_toolkit_tui import PromptToolkitTUI
        
        if not self.agent:
            show_error("AI agent not initialized")
            return
        
        # Create prompt_toolkit TUI with true embedded input
        tui = PromptToolkitTUI()
        
        # Set up logging handler to capture warnings and route to system footer
        class TUILogHandler(logging.Handler):
            def emit(self, record):
                try:
                    msg = self.format(record)
                    # Only show warnings and errors in footer
                    if record.levelno >= logging.WARNING:
                        tui.set_system_footer(msg)
                except Exception:
                    pass
        
        # Install logging handler for TUI mode and suppress console output
        tui_handler = TUILogHandler()
        tui_handler.setLevel(logging.WARNING)
        root_logger = logging.getLogger()
        
        # Remove existing handlers that print to console (stderr/stdout)
        original_handlers = root_logger.handlers[:]
        for handler in original_handlers:
            root_logger.removeHandler(handler)
        
        # Add our TUI handler
        root_logger.addHandler(tui_handler)
        root_logger.setLevel(logging.WARNING)
        
        # Set up system footer with model and context info
        model_name = self.settings.current_model if self.settings and self.settings.current_model else "not set"
        if not model_name or model_name == "not set":
            tui.set_system_footer(f"Model: {model_name} (using 4K context default) | Use /model to select a model")
        else:
            tui.set_system_footer(f"Model: {model_name}")
        
        # Define message handler with robust error handling
        async def handle_message(text: str) -> None:
            """Handle user message submission with comprehensive error handling."""
            try:
                # Check for exit commands
                if text.lower() in ["/exit", "/quit"]:
                    tui.exit()
                    return
                
                # Handle slash commands
                if text.startswith("/"):
                    # Add system message showing command
                    tui.conversation.add_message("system", f"Command: {text}")
                    tui.app.invalidate()
                    
                    # TODO: Integrate command execution in Phase 2
                    # For now, just acknowledge the command
                    tui.conversation.add_message("system", "Command execution in TUI will be available in Phase 2")
                    tui.app.invalidate()
                    return
                
                # Ensure agent is initialized
                if not self.agent:
                    tui.conversation.add_message("system", "Error: Agent not initialized")
                    tui.app.invalidate()
                    return
                
                # Start streaming AI response
                tui.start_streaming_response()
                
                # Stream response from agent with timeout protection
                chunk_count = 0
                try:
                    async for chunk, _ in self.agent.process_user_input_stream(text):
                        tui.append_streaming_chunk(chunk)
                        chunk_count += 1
                    
                    # If no chunks received, show error
                    if chunk_count == 0:
                        tui.conversation.add_message("system", "Warning: No response received from AI")
                        tui.app.invalidate()
                
                except asyncio.TimeoutError:
                    tui.conversation.add_message("system", "Error: Response timeout - AI took too long to respond")
                    tui.app.invalidate()
                except Exception as stream_error:
                    logger.error(f"Streaming error: {stream_error}", exc_info=True)
                    tui.conversation.add_message("system", f"Streaming error: {str(stream_error)}")
                    tui.app.invalidate()
                
                # Always finish streaming to unlock the UI
                tui.finish_streaming_response()
                
            except KeyboardInterrupt:
                # User interrupted streaming
                tui.conversation.add_message("system", "Response interrupted by user")
                tui.finish_streaming_response()
            except Exception as e:
                # Handle any unexpected errors
                logger.error(f"Error processing message: {e}", exc_info=True)
                # Make sure we always finish streaming even on error
                try:
                    tui.finish_streaming_response()
                except Exception:
                    pass
                tui.conversation.add_message("system", f"Unexpected error: {str(e)}")
                tui.app.invalidate()
        
        # Set message callback
        tui.set_message_callback(handle_message)
        
        # Set command callback with TUI reference
        async def command_handler(command: str, args: list[str]) -> str:
            """Wrapper to pass TUI instance to command handler."""
            return await self._handle_tui_command(command, args, tui=tui)
        
        tui.set_command_callback(command_handler)
        
        try:
            # Run the TUI (blocks until exit)
            await tui.run()
        except Exception as e:
            show_error(f"TUI error: {e}")
            if self.debug:
                console.print_exception()
        finally:
            # Restore original logging configuration
            root_logger.removeHandler(tui_handler)
            for handler in original_handlers:
                root_logger.addHandler(handler)
    
    async def _run_standard_mode(self) -> None:
        """Run in standard mode with separate prompts."""
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

    def run(self) -> None:
        """Run the main application loop."""
        try:
            asyncio.run(self.run_async())
        except Exception as e:
            show_error(f"Failed to start application: {e}")
            if self.debug:
                console.print_exception()
