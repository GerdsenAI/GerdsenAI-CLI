"""
Main application class for GerdsenAI CLI.

This module contains the core application logic and interactive loop.
"""

import asyncio
import contextlib
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .ui.prompt_toolkit_tui import PromptToolkitTUI

from rich.console import Console
from rich.prompt import Prompt

from .core.capabilities import CapabilityDetector, ModelCapabilities

logger = logging.getLogger(__name__)

from .commands.agent import (
    AgentConfigCommand,
    AgentStatusCommand,
    ChatCommand,
    RefreshContextCommand,
    ResetCommand,
)
from .commands.anthropic_cmd import AnthropicCommand
from .commands.audio_commands import (
    AudioStatusCommand,
    SpeakCommand,
    TranscribeCommand,
)
from .commands.discover import DiscoverCommand
from .commands.files import (
    CreateFileCommand,
    EditFileCommand,
    FilesCommand,
    ReadCommand,
    SearchFilesCommand,
    SessionCommand,
)
from .commands.index import IndexCommand
from .commands.mcp import MCPCommand
from .commands.model import (
    ListModelsCommand,
    ModelInfoCommand,
    ModelStatsCommand,
    SwitchModelCommand,
)

# Import command system
from .commands.parser import CommandParser
from .commands.persona import PersonaCommand
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
from .commands.vision_commands import (
    ImageCommand,
    OCRCommand,
    VisionStatusCommand,
)
from .config.manager import ConfigManager
from .config.settings import Settings
from .core.agent import Agent
from .core.errors import GerdsenAIError
from .core.llm_client import LLMClient
from .core.modes import ExecutionMode
from .plugins.registry import plugin_registry
from .utils.conversation_io import ConversationManager
from .utils.display import (
    show_error,
    show_info,
    show_startup_sequence,
    show_success,
    show_warning,
)

console = Console()


def _persist_agent_mode(agent: "Agent", mode: "ExecutionMode") -> None:
    """Mirror the TUI-selected execution mode into the Settings instance the agent
    reads fresh on every turn, so the CHAT/ARCHITECT/EXECUTE/LLVL selector actually
    drives the loop. The agent gates tools on settings.get_preference('agent_mode')
    in both _maybe_run_agent_loop and _tool_confirm; this is the write that was
    missing (the TUI updated its own ModeManager but never touched settings).
    agent.settings is the same Settings instance held by the CLI (Agent is
    constructed with it), so this in-memory write is seen on the next turn.
    """
    agent.settings.set_preference("agent_mode", mode.value)


class GerdsenAICLI:
    """Main GerdsenAI CLI application class."""

    def __init__(
        self,
        config_path: str | None = None,
        debug: bool = False,
        interactive: bool = True,
    ):
        """
        Initialize the GerdsenAI CLI.

        Args:
            config_path: Optional path to configuration file
            debug: Enable debug mode
            interactive: When False (headless one-shot mode), skip the interactive
                first-time setup wizard and fail fast instead of blocking on stdin.
        """
        self.debug = debug
        self.interactive = interactive
        self.config_manager = ConfigManager(config_path)
        self.settings: Settings | None = None
        self.running = False

        # Initialize components
        self.llm_client: LLMClient | None = None
        self.agent: Agent | None = None
        self.command_parser: CommandParser | None = None
        self.conversation_manager = ConversationManager()

        # Smart routing components (Phase 8d)
        self.smart_router: Any | None = None  # SmartRouter instance
        self.proactive_context: Any | None = None  # ProactiveContextBuilder instance

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
                if not self.interactive:
                    # Headless mode: never block on the interactive setup wizard
                    # (Prompt.ask would hang forever reading a piped stdin).
                    show_error(
                        "No configuration found. Run 'gerdsenai' once interactively "
                        "to set up, or point --config at an existing config file."
                    )
                    return False
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

            # Initialize AI agent with agentic capabilities
            self.agent = Agent(self.llm_client, self.settings)
            agent_ready = await self.agent.initialize()

            if not agent_ready:
                show_warning(
                    "Agent initialization failed, some features may be limited"
                )

            # Auto-refresh workspace context (like Claude CLI or Gemini CLI)
            # This ensures ARCHITECT mode can see repository files without manual commands
            if agent_ready and self.agent.context_manager:
                try:
                    logger.debug("Checking workspace context...")
                    # The project scan is lazy (runs on the first turn that needs
                    # context), so files is typically empty here -- report only
                    # when an eager scan has already populated it.
                    context_files = len(self.agent.context_manager.files)
                    if context_files > 0:
                        show_info(f"📂 Loaded {context_files} files into context")
                    else:
                        logger.debug(
                            "Project context will load on first use (lazy scan)"
                        )
                except Exception as e:
                    logger.warning(f"Failed to report workspace context: {e}")

            # Initialize command system
            await self._initialize_commands()

            # Initialize plugin system (Frontier AI)
            await self._initialize_plugins()

            # Initialize SmartRouter and ProactiveContextBuilder (Phase 8d)
            if self.settings.enable_smart_routing:
                from .core.proactive_context import ProactiveContextBuilder
                from .core.smart_router import SmartRouter

                self.smart_router = SmartRouter(
                    llm_client=self.llm_client,
                    settings=self.settings,
                    command_parser=self.command_parser,
                )

                # Get project root and context window for ProactiveContextBuilder
                project_root = Path.cwd()
                max_tokens = self.settings.model_context_window or 4096

                self.proactive_context = ProactiveContextBuilder(
                    project_root=project_root,
                    max_context_tokens=max_tokens,
                    context_usage_ratio=self.settings.context_window_usage,
                )

                show_info(
                    "🧠 Smart routing enabled - natural language commands supported!"
                )
            else:
                logger.info("SmartRouter disabled via configuration")

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
        self.command_parser.register_command(MCPCommand())

        # Register model commands
        self.command_parser.register_command(ListModelsCommand())
        self.command_parser.register_command(SwitchModelCommand())
        self.command_parser.register_command(ModelInfoCommand())
        self.command_parser.register_command(ModelStatsCommand())
        self.command_parser.register_command(DiscoverCommand())
        self.command_parser.register_command(IndexCommand())
        self.command_parser.register_command(AnthropicCommand())
        self.command_parser.register_command(PersonaCommand())

        # Register agent commands
        self.command_parser.register_command(AgentStatusCommand())
        self.command_parser.register_command(ChatCommand())
        self.command_parser.register_command(RefreshContextCommand())
        self.command_parser.register_command(ResetCommand())
        self.command_parser.register_command(AgentConfigCommand())
        if self.agent:
            # Register Phase 8d intelligence features
            from .commands.memory import MemoryCommand
            from .commands.planning import PlanCommand

            self.command_parser.register_command(PlanCommand(self.agent))
            self.command_parser.register_command(MemoryCommand(self.agent))

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

        # Register vision commands (Frontier AI Phase 2)
        self.command_parser.register_command(ImageCommand())
        self.command_parser.register_command(OCRCommand())
        self.command_parser.register_command(VisionStatusCommand())

        # Register audio commands (Frontier AI Phase 3)
        self.command_parser.register_command(TranscribeCommand())
        self.command_parser.register_command(SpeakCommand())
        self.command_parser.register_command(AudioStatusCommand())

        # Register imported skills/agent files (.claude/skills, .claude/agents,
        # AGENTS.md) as slash commands and fold a summary into the agent's
        # system prompt. Read-only; no-op when none are present.
        self._register_imported_skills()

        # Apply the active agent profile (persona + model), if one is set.
        self._apply_active_persona()

    def _apply_active_persona(self) -> None:
        """Fold the active agent profile's persona into the agent."""
        from .core.agent_profiles import AgentProfileManager

        profile = AgentProfileManager(self.config_manager).get_active()
        if profile and self.agent is not None and profile.system_prompt:
            self.agent.persona_context = profile.system_prompt

    def _register_imported_skills(self) -> None:
        """Discover external skill/agent files and expose them."""
        from .commands.skills import SkillCommand, SkillsCommand
        from .core.skill_loader import build_skills_context, discover_skills

        if self.command_parser is None:
            return

        skills = discover_skills()
        for skill in skills:
            # Never clobber a built-in command of the same name.
            if self.command_parser.registry.get_command(skill.command_name) is None:
                self.command_parser.register_command(SkillCommand(skill))
        self.command_parser.register_command(SkillsCommand(skills))

        if self.agent is not None and skills:
            self.agent.skills_context = build_skills_context(skills)

    async def _initialize_plugins(self) -> None:
        """
        Initialize the plugin system and discover plugins.

        Automatically discovers and registers plugins from the plugins directory.
        Plugins (Vision, Audio) are registered but not initialized
        until first use (lazy loading for performance).
        """

        from .plugins.audio.bark_plugin import BarkPlugin
        from .plugins.audio.whisper_plugin import WhisperPlugin
        from .plugins.vision.llava_plugin import LLaVAPlugin
        from .plugins.vision.tesseract_ocr import TesseractOCRPlugin

        try:
            logger.info("Initializing plugin system...")

            # Register vision plugins (Phase 2)
            try:
                llava = LLaVAPlugin()
                plugin_registry.register(llava)
                logger.info("Registered LLaVA vision plugin")
            except Exception as e:
                logger.debug(f"Could not register LLaVA plugin: {e}")

            try:
                tesseract = TesseractOCRPlugin()
                plugin_registry.register(tesseract)
                logger.info("Registered Tesseract OCR plugin")
            except Exception as e:
                logger.debug(f"Could not register Tesseract plugin: {e}")

            # Register audio plugins (Phase 3)
            try:
                whisper = WhisperPlugin()
                plugin_registry.register(whisper)
                logger.info("Registered Whisper audio plugin")
            except Exception as e:
                logger.debug(f"Could not register Whisper plugin: {e}")

            try:
                bark = BarkPlugin()
                plugin_registry.register(bark)
                logger.info("Registered Bark TTS plugin")
            except Exception as e:
                logger.debug(f"Could not register Bark plugin: {e}")

            # Note: Plugins are NOT initialized here for performance
            # They will be initialized on first use (lazy loading)
            logger.info("Plugin system ready (plugins will initialize on first use)")

        except Exception as e:
            logger.warning(f"Plugin initialization error: {e}")
            # Non-fatal - continue without plugins

    async def _first_time_setup(self) -> Settings | None:
        """
        Handle first-time setup process.

        Returns:
            Settings object if setup successful, None otherwise
        """
        try:
            console.print("\n[SETUP] [bold cyan]GerdsenAI CLI Setup[/bold cyan]\n")

            # Try auto-discovery first (local ports + Tailscale peers); the user
            # can always fall back to entering a server manually.
            endpoint: tuple[str, str, int] | None = None
            discovered = await self._discover_servers_for_setup()
            if discovered:
                show_success(f"Found {len(discovered)} LLM server(s) on your network:")
                for i, dp in enumerate(discovered, 1):
                    console.print(f"  {i}. {dp.url}  [{dp.source}]")
                manual_choice = str(len(discovered) + 1)
                console.print(f"  {manual_choice}. Enter a server manually")
                choice = Prompt.ask(
                    "Select a server",
                    choices=[str(i) for i in range(1, len(discovered) + 2)],
                    default="1",
                    console=console,
                )
                if choice != manual_choice:
                    endpoint = self._endpoint_from_provider(discovered[int(choice) - 1])
                    show_info(
                        f"Using discovered server: "
                        f"{endpoint[0]}://{endpoint[1]}:{endpoint[2]}"
                    )

            if endpoint is not None:
                protocol, host, port = endpoint
            else:
                # Manual server configuration
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
                    logger.debug(f"Attempting connection to {protocol}://{host}:{port}")
                    connected = await asyncio.wait_for(
                        temp_client.connect(),
                        timeout=15.0,  # 15 second total timeout for setup
                    )
                    logger.debug(f"Connection result: {connected}")

                    if not connected:
                        show_error(
                            "Could not connect to the LLM server. Please check the URL and try again."
                        )
                        return None

                    # Get available models
                    models = await temp_client.list_models()
            except TimeoutError:
                logger.debug("Connection test timed out after 15 seconds")
                show_error(
                    "Connection test timed out. Please check if your LLM server is running and accessible."
                )
                return None
            except Exception as e:
                logger.debug(f"Connection test failed with exception: {e}")
                show_error(f"Connection test failed: {e}")
                return None

            default_model = ""
            if models:
                show_success(f"Connected! Found {len(models)} available models:")
                for i, model in enumerate(models[:5]):  # Show first 5 models
                    console.print(f"  {i + 1}. {model.id}")

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

    async def _discover_servers_for_setup(self) -> list:
        """Best-effort discovery of local + Tailscale LLM servers for setup.

        Returns an empty list (never raises) when discovery is unavailable, so
        first-run setup always falls back cleanly to manual entry.
        """
        try:
            from .core.providers.detector import ProviderDetector

            show_info("Scanning for local and Tailscale LLM servers...")
            return await ProviderDetector().discover()
        except Exception as e:
            logger.debug(f"Setup discovery failed, falling back to manual: {e}")
            return []

    @staticmethod
    def _endpoint_from_provider(dp: Any) -> tuple[str, str, int]:
        """Map a discovered provider URL to (protocol, host, port)."""
        from urllib.parse import urlparse

        parsed = urlparse(dp.url)
        return (
            parsed.scheme or "http",
            parsed.hostname or "127.0.0.1",
            parsed.port or 11434,
        )

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

        This is a fallback path used outside the main TUI loop.

        Args:
            message: The chat message

        Returns:
            True to continue running, False to exit
        """
        if not self.agent:
            show_error("AI agent not initialized")
            return True

        try:
            streaming_enabled = (
                self.settings.user_preferences.get("streaming", True)
                if self.settings
                else True
            )

            if streaming_enabled:
                console.print(f"\n[bold green]You:[/bold green] {message}")
                console.print("[bold cyan]GerdsenAI:[/bold cyan]", end=" ")

                async for (
                    chunk,
                    _full_response,
                ) in self.agent.process_user_input_stream(message):
                    console.print(chunk, end="", style="white")

                console.print()  # Final newline
            else:
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
            await self._run_persistent_tui_mode()

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
            if self.llm_client:
                # Properly exit async context manager
                await self.llm_client.__aexit__(None, None, None)

    async def _handle_tui_command(
        self, command: str, args: list[str], tui: "PromptToolkitTUI | None" = None
    ) -> str:
        """Handle TUI commands like /model, /save, /load, /export.

        Args:
            command: The command string (e.g., '/model')
            args: List of command arguments
            tui: Optional TUI instance for accessing conversation data

        Returns:
            Response string to display to user
        """
        try:
            if command == "/model":
                if not args:
                    # Show current model
                    current = (
                        self.settings.current_model
                        if self.settings and self.settings.current_model
                        else "not set"
                    )
                    return f"Current model: {current}\n\nUse '/model <name>' to switch models."
                else:
                    # Switch to new model
                    new_model = args[0]
                    if self.settings:
                        self.settings.current_model = new_model
                        if self.agent and hasattr(self.agent, "settings"):
                            self.agent.settings.current_model = new_model

                        # Update TUI footer if TUI is available
                        if tui:
                            tui.set_system_footer(f"Model: {new_model}")

                        return f"Switched to model: {new_model}"
                    else:
                        return "Error: Settings not initialized"

            elif command == "/save":
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
                    "model": self.settings.current_model
                    if self.settings
                    else "unknown",
                    "message_count": len(messages),
                }

                # Save conversation
                try:
                    assert (
                        filename is not None
                    )  # filename is always set in /save command
                    filepath = self.conversation_manager.save_conversation(
                        filename, messages, metadata
                    )
                    return f"Conversation saved successfully!\n\nFile: {filepath}\nMessages: {len(messages)}"
                except Exception as e:
                    logger.error(f"Error saving conversation: {e}", exc_info=True)
                    return f"Error saving conversation: {str(e)}"

            elif command == "/load":
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
                    messages, metadata = self.conversation_manager.load_conversation(
                        filename
                    )

                    # Clear current conversation
                    tui.conversation.clear_messages()

                    # Load messages into TUI
                    for role, content, _ in messages:
                        tui.conversation.add_message(role, content)

                    # Build response
                    msg_count = len(messages)
                    lines = [
                        "Conversation loaded successfully!",
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

            elif command == "/resume":
                if not tui:
                    return "Error: TUI not available for resume operation"

                filename = args[0] if args else None  # type: ignore[assignment]

                # If no filename provided, resume most recent conversation
                if not filename:
                    conversations = self.conversation_manager.list_conversations()
                    if not conversations:
                        return "No saved conversations found.\n\nUse '/save <filename>' to save a conversation first."

                    # Get most recent conversation (conversations are sorted by modification time)
                    filename = conversations[0].stem
                    logger.info(f"Resuming most recent conversation: {filename}")

                # Ensure filename is set
                assert filename is not None, "filename must be set"

                # Load conversation
                try:
                    messages, metadata = self.conversation_manager.load_conversation(
                        filename
                    )

                    # Clear current conversation
                    tui.conversation.clear_messages()

                    # Load messages into TUI
                    for role, content, _ in messages:
                        tui.conversation.add_message(role, content)

                    # Get memory context if available
                    memory_context = ""
                    if (
                        self.agent
                        and hasattr(self.agent, "memory")
                        and self.agent.memory
                    ):
                        context_summary = self.agent.memory.get_context_summary()
                        if context_summary.strip():
                            memory_context = (
                                f"\n\nRelevant context from memory:\n{context_summary}"
                            )

                    # Build response
                    msg_count = len(messages)
                    lines = [
                        f"Resumed conversation: {filename}",
                        f"Messages restored: {msg_count}",
                    ]

                    if metadata:
                        if metadata.get("model"):
                            lines.append(f"Model: {metadata['model']}")

                    if memory_context:
                        lines.append(memory_context)

                    return "\n".join(lines)

                except FileNotFoundError:
                    return f"Conversation not found: {filename}\n\nUse '/load' to list available conversations."
                except Exception as e:
                    logger.error(f"Error resuming conversation: {e}", exc_info=True)
                    return f"Error resuming conversation: {str(e)}"

            elif command == "/clarify":
                from .commands.clarify_commands import ClarifyCommand

                clarify_cmd = ClarifyCommand()
                clarify_cmd.agent = self.agent
                clarify_cmd.console = console

                return await clarify_cmd.execute(args)

            elif command == "/complexity":
                from .commands.complexity_commands import ComplexityCommand

                complexity_cmd = ComplexityCommand()
                complexity_cmd.agent = self.agent
                complexity_cmd.console = console

                return await complexity_cmd.execute(args)

            elif command == "/undo":
                from .commands.undo_commands import UndoCommand

                undo_cmd = UndoCommand()
                undo_cmd.agent = self.agent
                undo_cmd.console = console

                return await undo_cmd.execute(args)

            elif command == "/suggest":
                from .commands.suggest_commands import SuggestCommand

                suggest_cmd = SuggestCommand()
                suggest_cmd.agent = self.agent
                suggest_cmd.console = console

                return await suggest_cmd.execute(args)

            elif command == "/export":
                if not tui:
                    return "Error: TUI not available for export operation"

                # Get conversation messages from TUI
                messages = tui.conversation.messages

                if not messages:
                    return "No messages to export. Start a conversation first."

                filename = args[0] if args else None  # type: ignore[assignment]

                # Prepare metadata
                metadata = {
                    "model": self.settings.current_model
                    if self.settings
                    else "unknown",
                    "message_count": len(messages),
                    "exported_at": datetime.now().isoformat(),
                }

                # Export conversation
                try:
                    filepath = self.conversation_manager.export_conversation(
                        filename, messages, metadata
                    )
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
            def emit(self, record: logging.LogRecord) -> None:
                try:
                    msg = self.format(record)
                    # Only show warnings and errors in footer
                    if record.levelno >= logging.WARNING:
                        tui.set_system_footer(msg)
                except Exception as e:
                    # Log handler failure - use stderr as fallback to avoid infinite loop
                    import sys

                    print(f"TUI log handler failed: {e}", file=sys.stderr)

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
        model_name = (
            self.settings.current_model
            if self.settings and self.settings.current_model
            else "not set"
        )
        if not model_name or model_name == "not set":
            tui.set_system_footer(
                f"Model: {model_name} (using 4K context default) | Use /model to select a model"
            )
        else:
            tui.set_system_footer(f"Model: {model_name}")

        # Track model capabilities (detect once on first use)
        capabilities: ModelCapabilities | None = None

        # Initialize TUI edge case handler for robust error handling
        from .ui.tui_edge_cases import TUIEdgeCaseHandler

        tui_edge_handler = TUIEdgeCaseHandler()

        # Define message handler with robust error handling
        async def handle_message(text: str) -> None:
            """Handle user message submission with comprehensive error handling."""
            nonlocal capabilities

            try:
                # Check for exit commands
                if text.lower() in ["/exit", "/quit"]:
                    tui.exit()
                    return

                # Edge case handling: Validate and sanitize input
                try:
                    (
                        sanitized_text,
                        warnings,
                    ) = await tui_edge_handler.validate_and_process_input(text)

                    # Show any warnings to user
                    for warning in warnings:
                        tui.conversation.add_message("system", warning)
                        tui.app.invalidate()

                    # Use sanitized text for processing
                    text = sanitized_text

                except GerdsenAIError as e:
                    # Input validation failed - show error and return
                    from .ui.error_display import ErrorDisplay

                    error_msg = ErrorDisplay.display_error(
                        e, show_details=False, tui_mode=False
                    )
                    tui.conversation.add_message("system", error_msg)
                    tui.app.invalidate()
                    return

                # Memory management: Archive old messages if needed
                archive_notice = tui_edge_handler.manage_conversation_memory(
                    tui.conversation.messages, tui.conversation
                )
                if archive_notice:
                    tui.conversation.add_message("system", archive_notice)
                    tui.app.invalidate()

                # Phase 8d: SmartRouter Integration
                # Use SmartRouter for intelligent routing if enabled
                if (
                    self.smart_router
                    and self.settings
                    and self.settings.enable_smart_routing
                ):
                    from .core.smart_router import RouteType

                    # Get project files for context
                    project_files = []
                    if (
                        self.agent
                        and hasattr(self.agent, "context_manager")
                        and self.agent.context_manager
                    ):
                        project_files = [
                            str(f.relative_path)
                            for f in self.agent.context_manager.files.values()
                        ]

                    # Route the input
                    try:
                        route_decision = await self.smart_router.route(
                            text, project_files
                        )

                        # Handle slash command routing
                        if route_decision.route_type == RouteType.SLASH_COMMAND:
                            tui.conversation.add_message("system", f"Command: {text}")
                            tui.app.invalidate()
                            # For now, acknowledge - full command execution to be added
                            tui.conversation.add_message(
                                "system",
                                "Command execution in TUI will be enhanced in next phase",
                            )
                            tui.app.invalidate()
                            return

                        # Handle clarification request
                        elif route_decision.route_type == RouteType.CLARIFICATION:
                            tui.conversation.add_message(
                                "system", route_decision.clarification_prompt
                            )
                            tui.app.invalidate()
                            return

                        # Handle natural language intent
                        elif route_decision.route_type == RouteType.NATURAL_LANGUAGE:
                            intent = route_decision.intent
                            show_msg = f"💡 Detected intent: {intent.action_type.value}"
                            if intent.parameters.get("files"):
                                show_msg += f"\n📄 Files: {', '.join(intent.parameters['files'][:3])}"
                            if intent.reasoning:
                                show_msg += f"\n💭 {intent.reasoning}"
                            tui.conversation.add_message("system", show_msg)
                            tui.app.invalidate()
                            # Continue to process as chat with enhanced context

                        # For PASSTHROUGH_CHAT and NATURAL_LANGUAGE, continue to normal processing

                    except Exception as e:
                        logger.error(f"SmartRouter error: {e}", exc_info=True)
                        tui.conversation.add_message(
                            "system",
                            "⚠️  Routing error, falling back to standard processing",
                        )
                        tui.app.invalidate()

                # Fallback: Handle slash commands directly if SmartRouter not enabled
                elif text.startswith("/"):
                    tui.conversation.add_message("system", f"Command: {text}")
                    tui.app.invalidate()
                    tui.conversation.add_message(
                        "system",
                        "Command execution in TUI will be enhanced in next phase",
                    )
                    tui.app.invalidate()
                    return

                # Ensure agent is initialized
                if not self.agent:
                    tui.conversation.add_message(
                        "system", "Error: Agent not initialized"
                    )
                    tui.app.invalidate()
                    return

                # Detect capabilities on first message if not already done
                if capabilities is None:
                    try:
                        model_name = (
                            self.settings.current_model if self.settings else None
                        )
                        if model_name:
                            capabilities = CapabilityDetector.detect_from_model_name(
                                model_name
                            )

                            # Show capability summary to user
                            cap_msg = f"🔍 Model: {model_name}\n"
                            cap_msg += f"  • Thinking: {'✅ Supported' if capabilities.supports_thinking else '❌ Not supported'}\n"
                            cap_msg += f"  • Vision: {'✅ Supported' if capabilities.supports_vision else '❌ Not supported'}\n"
                            cap_msg += f"  • Tools: {'✅ Supported' if capabilities.supports_tools else '❌ Not supported'}\n"
                            cap_msg += f"  • Streaming: {'✅ Supported' if capabilities.supports_streaming else '❌ Not supported'}"

                            tui.conversation.add_message("system", cap_msg)
                            tui.app.invalidate()

                            logger.info(
                                f"Detected capabilities for {model_name}: thinking={capabilities.supports_thinking}, vision={capabilities.supports_vision}, tools={capabilities.supports_tools}, streaming={capabilities.supports_streaming}"
                            )

                            # Warn if thinking is enabled but not supported
                            if (
                                tui.thinking_enabled
                                and not capabilities.supports_thinking
                            ):
                                tui.conversation.add_message(
                                    "system",
                                    "⚠️  Thinking mode is enabled but this model does not support structured thinking output",
                                )
                                tui.app.invalidate()
                    except Exception as e:
                        logger.warning(f"Failed to detect capabilities: {e}")
                        # Use defaults if detection fails
                        capabilities = ModelCapabilities()

                # Import for plan capture
                from .ui.animations import PlanCapture

                # Check if we're in approval mode
                if tui.approval_mode and tui.pending_plan:
                    # Handle approval response
                    approved = await tui.handle_approval_response(text)

                    if approved:
                        # Switch to EXECUTE mode and execute the plan
                        from .core.modes import ExecutionMode

                        old_mode = tui.mode_manager.get_mode()
                        tui.mode_manager.set_mode(ExecutionMode.EXECUTE)

                        # Show executing animation
                        tui.show_animation("Executing plan", "executing")

                        try:
                            # Get the original user request from pending_plan metadata
                            # For now, use the full response as context
                            original_request = tui.pending_plan.get(
                                "original_request", text
                            )

                            # Execute with streaming display
                            await asyncio.sleep(0.5)  # Brief pause for UX
                            tui.hide_animation()
                            tui.start_streaming_response()

                            chunk_count = 0
                            async for chunk, _ in self.agent.process_user_input_stream(
                                original_request
                            ):
                                tui.append_streaming_chunk(chunk)
                                chunk_count += 1

                                if tui.streaming_chunk_delay > 0:
                                    await asyncio.sleep(tui.streaming_chunk_delay)

                                if chunk_count % tui.streaming_refresh_interval == 0:
                                    tui.app.invalidate()

                            tui.finish_streaming_response()
                            tui.conversation.add_message(
                                "command", "✅ Execution complete!"
                            )

                        except asyncio.CancelledError:
                            # User pressed Escape during plan execution: keep
                            # partial text + cancel marker, finalize, restore
                            # mode via finally below.
                            logger.info("Plan execution cancelled by user")
                            tui.hide_animation()
                            if tui.conversation.streaming_message is not None:
                                tui.append_streaming_chunk(
                                    "\n\n_⏹ Response cancelled._"
                                )
                            tui.finish_streaming_response()

                        except Exception as e:
                            tui.hide_animation()
                            tui.finish_streaming_response()
                            tui.conversation.add_message(
                                "system", f"Execution error: {str(e)}"
                            )
                            logger.error(f"Execution error: {e}", exc_info=True)

                        finally:
                            # Restore original mode
                            tui.mode_manager.set_mode(old_mode)
                            mode_name = old_mode.value.upper()
                            tui.status_text = f"[{mode_name}] Ready. Type your message and press Enter."
                            tui.pending_plan = None

                    tui.app.invalidate()
                    return

                # Get current mode
                current_mode = tui.get_mode()

                # Mode sync: the agent reads 'agent_mode' from settings each turn,
                # so push the TUI's live selection into the shared Settings instance
                # before dispatching. This single write covers every mode branch
                # below (CHAT / ARCHITECT / EXECUTE / LLVL) since they all run after
                # this point in the same handler. (self.agent.settings IS
                # self.settings — Agent is constructed with it in initialize().)
                if self.agent:
                    _persist_agent_mode(self.agent, current_mode)

                # In CHAT mode, check if user is requesting action
                if current_mode == ExecutionMode.CHAT:
                    action_keywords = [
                        "create",
                        "delete",
                        "modify",
                        "update",
                        "change",
                        "fix",
                        "add",
                        "remove",
                        "refactor",
                        "write",
                        "edit",
                        "implement",
                    ]
                    if any(keyword in text.lower() for keyword in action_keywords):
                        suggestion = (
                            "💡 It looks like you're requesting an action. "
                            "In CHAT mode, I can only provide information and guidance.\n\n"
                            "To execute actions:\n"
                            "  • Switch to ARCHITECT mode (/mode architect) to plan changes\n"
                            "  • Switch to EXECUTE mode (/mode execute) to make changes directly\n"
                            "  • Use Shift+Tab to cycle through modes"
                        )
                        tui.conversation.add_message("system", suggestion)
                        tui.app.invalidate()
                        return

                    # Regular CHAT mode conversation - stream AI response

                    # Phase 8d: Proactive Context Building
                    context_summary = ""
                    if (
                        self.proactive_context
                        and self.settings
                        and self.settings.enable_proactive_context
                    ):
                        try:
                            # Build smart context from mentioned files
                            conversation_history = (
                                [
                                    msg.content
                                    for msg in self.smart_router.conversation_history[
                                        -10:
                                    ]
                                ]
                                if self.smart_router
                                else []
                            )
                            context_files = (
                                await self.proactive_context.build_smart_context(
                                    user_query=text,
                                    conversation_history=conversation_history,
                                )
                            )

                            if context_files:
                                file_count = len(context_files)
                                tui.conversation.add_message(
                                    "system",
                                    f"📖 Auto-loaded {file_count} file(s) for context",
                                )
                                tui.app.invalidate()

                                # Build context summary for better responses (optimized string building)
                                parts = ["\n\n# Context Files:\n"]
                                for file_path, result in context_files.items():
                                    parts.append(f"\n## {file_path}\n")
                                    parts.append(f"_({result.read_reason})_\n")
                                    if result.truncated:
                                        parts.append(
                                            "_Content truncated for context window_\n"
                                        )
                                    parts.append(f"\n```\n{result.content}\n```\n")
                                context_summary = "".join(parts)

                        except Exception as e:
                            logger.warning(f"ProactiveContext error: {e}")
                            # Continue without enhanced context

                    # Enhance user input with context if available
                    enhanced_text = text + context_summary if context_summary else text

                    # Mark streaming start for state guard
                    tui_edge_handler.state_guard.mark_streaming_start()
                    tui_edge_handler.stream_recovery.start_stream()
                    tui.start_streaming_response()

                    chunk_count = 0
                    try:
                        async for chunk, _ in self.agent.process_user_input_stream(
                            enhanced_text
                        ):
                            # Record chunk for health monitoring
                            tui_edge_handler.stream_recovery.record_chunk()

                            # Check stream health
                            is_healthy, error = (
                                tui_edge_handler.stream_recovery.check_health()
                            )
                            if not is_healthy:
                                logger.error(f"Stream health check failed: {error}")
                                from .core.errors import (
                                    TimeoutError as GerdsenAITimeoutError,
                                )

                                raise GerdsenAITimeoutError(
                                    message=f"Stream failed: {error}",
                                    timeout_seconds=tui_edge_handler.stream_recovery.timeout_seconds,
                                )

                            tui.append_streaming_chunk(chunk)
                            chunk_count += 1

                            # Add configurable delay for smooth typewriter animation
                            if tui.streaming_chunk_delay > 0:
                                await asyncio.sleep(tui.streaming_chunk_delay)

                            # Periodic refresh for smooth rendering
                            if chunk_count % tui.streaming_refresh_interval == 0:
                                tui.app.invalidate()

                        # If no chunks received, show error
                        if chunk_count == 0:
                            tui.conversation.add_message(
                                "system", "Warning: No response received from AI"
                            )
                            tui.app.invalidate()

                        # Record success for provider health tracking
                        tui_edge_handler.provider_handler.record_success()

                    except asyncio.CancelledError:
                        # User pressed Escape mid-stream: mark the cancellation
                        # inline on the partial text (the "system" channel isn't
                        # rendered), then finalize so it lands in visible history.
                        # Do not re-raise -- the app loop keeps accepting input.
                        logger.info("Streaming response cancelled by user")
                        if tui.conversation.streaming_message is not None:
                            tui.append_streaming_chunk("\n\n_⏹ Response cancelled._")
                        tui.finish_streaming_response()  # finally's call no-ops
                        tui.app.invalidate()

                    except TimeoutError:
                        # Record provider failure
                        tui_edge_handler.provider_handler.record_failure()

                        # Get recovery message
                        recovery_msg = (
                            tui_edge_handler.stream_recovery.get_recovery_message(
                                "Response timeout"
                            )
                        )
                        tui.conversation.add_message("system", recovery_msg)
                        tui.app.invalidate()

                    except Exception as stream_error:
                        logger.error(f"Streaming error: {stream_error}", exc_info=True)

                        # Record provider failure
                        tui_edge_handler.provider_handler.record_failure()

                        # Get appropriate recovery message
                        error_str = str(stream_error)
                        recovery_msg = (
                            tui_edge_handler.stream_recovery.get_recovery_message(
                                error_str
                            )
                        )

                        # Add provider-specific recovery if multiple failures
                        if tui_edge_handler.provider_handler.should_show_recovery_help():
                            provider_recovery = (
                                tui_edge_handler.provider_handler.get_recovery_message(
                                    stream_error
                                )
                            )
                            recovery_msg += "\n\n" + provider_recovery

                        tui.conversation.add_message("system", recovery_msg)
                        tui.app.invalidate()

                    finally:
                        # Always mark streaming end and finish streaming to unlock the UI
                        tui_edge_handler.state_guard.mark_streaming_end()
                        tui.finish_streaming_response()
                        tui.app.invalidate()

                    return

                # In ARCHITECT mode, show thinking animation and capture response for approval
                if current_mode == ExecutionMode.ARCHITECT:
                    # Phase 8d: Proactive Context Building
                    context_summary = ""
                    if (
                        self.proactive_context
                        and self.settings
                        and self.settings.enable_proactive_context
                    ):
                        try:
                            tui.show_animation("Loading context", "reading")
                            conversation_history = (
                                [
                                    msg.content
                                    for msg in self.smart_router.conversation_history[
                                        -10:
                                    ]
                                ]
                                if self.smart_router
                                else []
                            )
                            context_files = (
                                await self.proactive_context.build_smart_context(
                                    user_query=text,
                                    conversation_history=conversation_history,
                                )
                            )

                            if context_files:
                                file_count = len(context_files)
                                tui.hide_animation()
                                tui.conversation.add_message(
                                    "system",
                                    f"📖 Auto-loaded {file_count} file(s) for planning",
                                )
                                tui.app.invalidate()

                                # Optimized string building for better performance
                                parts = ["\n\n# Context Files:\n"]
                                for file_path, result in context_files.items():
                                    parts.append(f"\n## {file_path}\n")
                                    parts.append(f"_({result.read_reason})_\n")
                                    if result.truncated:
                                        parts.append("_Content truncated_\n")
                                    parts.append(f"\n```\n{result.content}\n```\n")
                                context_summary = "".join(parts)

                        except Exception as e:
                            logger.warning(f"ProactiveContext error: {e}")

                    enhanced_text = text + context_summary if context_summary else text

                    # Show thinking animation
                    tui.show_animation("Analyzing your request", "thinking")
                    await asyncio.sleep(0.5)  # Brief pause for UX

                    tui.show_animation("Creating execution plan", "planning")

                    try:
                        # Capture AI response silently (don't stream to screen)
                        full_response = ""
                        async for chunk, _ in self.agent.process_user_input_stream(
                            enhanced_text
                        ):
                            full_response += chunk
                            # Update animation message periodically
                            if len(full_response) % 200 == 0 and tui.current_animation:
                                tui.current_animation.update_message(
                                    "Planning... (analyzing complexity)"
                                )

                        # Stop animation
                        tui.hide_animation()

                        # Extract and show plan summary
                        plan = PlanCapture.extract_summary(full_response)
                        plan["original_request"] = text  # Store for later execution
                        tui.show_plan_for_approval(plan)

                    except asyncio.CancelledError:
                        # User pressed Escape during planning: clean up and
                        # return to the prompt without surfacing a fake error.
                        logger.info("Planning cancelled by user")
                        tui.hide_animation()
                        tui.app.invalidate()
                        return

                    except Exception as e:
                        tui.hide_animation()
                        tui.conversation.add_message(
                            "system", f"Planning error: {str(e)}"
                        )
                        logger.error(f"Planning error: {e}", exc_info=True)

                    tui.app.invalidate()
                    return

                # In EXECUTE or LLVL mode, execute immediately with brief animation
                if current_mode in [ExecutionMode.EXECUTE, ExecutionMode.LLVL]:
                    # Phase 8d: Proactive Context Building
                    context_summary = ""
                    if (
                        self.proactive_context
                        and self.settings
                        and self.settings.enable_proactive_context
                    ):
                        try:
                            tui.show_animation("Loading context", "reading")
                            conversation_history = (
                                [
                                    msg.content
                                    for msg in self.smart_router.conversation_history[
                                        -10:
                                    ]
                                ]
                                if self.smart_router
                                else []
                            )
                            context_files = (
                                await self.proactive_context.build_smart_context(
                                    user_query=text,
                                    conversation_history=conversation_history,
                                )
                            )

                            if context_files:
                                file_count = len(context_files)
                                tui.hide_animation()
                                tui.conversation.add_message(
                                    "system", f"📖 Auto-loaded {file_count} file(s)"
                                )
                                tui.app.invalidate()

                                context_summary = "\n\n# Context Files:\n"
                                for file_path, result in context_files.items():
                                    context_summary += f"\n## {file_path}\n```\n{result.content}\n```\n"

                        except Exception as e:
                            logger.warning(f"ProactiveContext error: {e}")

                    enhanced_text = text + context_summary if context_summary else text

                    tui.show_animation("Executing", "executing")

                    # Brief delay for UX
                    await asyncio.sleep(0.3)

                    # Execute with streaming
                    tui.hide_animation()
                    tui.start_streaming_response()

                    chunk_count = 0
                    try:
                        async for chunk, _ in self.agent.process_user_input_stream(
                            enhanced_text
                        ):
                            tui.append_streaming_chunk(chunk)
                            chunk_count += 1

                            # Add configurable delay for smooth typewriter animation
                            if tui.streaming_chunk_delay > 0:
                                await asyncio.sleep(tui.streaming_chunk_delay)

                            # Periodic refresh for smooth rendering
                            if chunk_count % tui.streaming_refresh_interval == 0:
                                tui.app.invalidate()

                        # If no chunks received, show error
                        if chunk_count == 0:
                            tui.conversation.add_message(
                                "system", "Warning: No response received from AI"
                            )
                            tui.app.invalidate()

                    except asyncio.CancelledError:
                        # User pressed Escape mid-execution: keep partial text +
                        # inline cancel marker, then finalize below.
                        logger.info("Execution response cancelled by user")
                        if tui.conversation.streaming_message is not None:
                            tui.append_streaming_chunk("\n\n_⏹ Response cancelled._")

                    except TimeoutError:
                        timeout_value = (
                            self.settings.api_timeout if self.settings else 120
                        )
                        timeout_msg = (
                            f"⏱️  Response Timeout ({timeout_value}s exceeded)\n\n"
                            "**What happened?**\n"
                            "The AI didn't respond within the timeout limit.\n\n"
                            "**How to fix:**\n"
                            "• Try a shorter message or reduce context\n"
                            "• Check if your LLM provider is overloaded\n"
                            "• Increase timeout: `/config` → set api_timeout\n"
                            "• Switch to faster model: `/model`\n"
                            "• Reduce context window usage in settings"
                        )
                        tui.conversation.add_message("system", timeout_msg)
                        tui.app.invalidate()
                    except Exception as stream_error:
                        logger.error(f"Streaming error: {stream_error}", exc_info=True)
                        tui.conversation.add_message(
                            "system", f"Streaming error: {str(stream_error)}"
                        )
                        tui.app.invalidate()

                    # Always finish streaming to unlock the UI
                    tui.finish_streaming_response()
                    tui.app.invalidate()
                    return

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
                except Exception as finish_error:
                    # Even finishing streaming failed - log but don't crash
                    logger.error(
                        f"Failed to finish streaming after error: {finish_error}"
                    )
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

    def run(self) -> None:
        """Run the main application loop."""
        try:
            asyncio.run(self.run_async())
        except Exception as e:
            show_error(f"Failed to start application: {e}")
            if self.debug:
                console.print_exception()

    async def run_headless(self, prompt: str, mode: str = "execute") -> int:
        """Run a single agent turn non-interactively, print the answer, and exit.

        Backs ``gerdsenai -p``/``--stdin``. Returns a process exit code: 0 on
        success, 1 on failure (no config, no model selected, or an error).

        Consent stays sacred: there is no interactive confirm callback here, so
        mutating tools remain gated by ``auto_confirm_edits`` (default False) /
        LLVL — headless runs are read-only-safe unless explicitly opted in.
        """
        from .utils.display import set_quiet_mode

        # stdout must carry ONLY the answer (clean piping). set_quiet_mode routes
        # the display console to stderr; redirect_stdout catches every OTHER
        # console/print emitted during the run (init banners, the agent's project
        # analysis + context-building progress, the interactive "GerdsenAI:" echo)
        # so they don't pollute the pipe. The answer is printed after the block,
        # to the restored real stdout.
        set_quiet_mode(True)
        answer = ""
        with contextlib.redirect_stdout(sys.stderr):
            if not await self.initialize():
                return 1

            # Honor the requested mode (default 'execute' so the tool loop runs;
            # pass --mode chat for pure Q&A). Mutations still gate on
            # auto_confirm_edits because there is no TUI confirm callback.
            if self.settings is not None:
                self.settings.set_preference("agent_mode", mode)

            if not self.agent or not self.settings or not self.settings.current_model:
                show_error(
                    "No model selected. Set 'current_model' in your config file "
                    "(or run 'gerdsenai' interactively once to pick one)."
                )
                await self._headless_cleanup()
                return 1

            try:
                answer = await self.agent.process_user_input(prompt)
            except Exception as e:  # noqa: BLE001 - report and exit non-zero
                show_error(str(e))
                return 1
            finally:
                await self._headless_cleanup()

        print(answer)
        return 0

    async def _headless_cleanup(self) -> None:
        """Release agent + LLM client resources after a headless run."""
        if self.agent:
            await self.agent.cleanup()
        if self.llm_client:
            await self.llm_client.__aexit__(None, None, None)
