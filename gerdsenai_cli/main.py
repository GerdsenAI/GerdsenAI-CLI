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
from .utils.display import show_error, show_info, show_success, show_warning

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
        self.agent = None
        self.context_manager = None
        
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
            
            # TODO: Initialize agent and context manager
            # This will be implemented in Phase 4
            
            show_success("GerdsenAI CLI initialized successfully!")
            return True
            
        except Exception as e:
            show_error(f"Failed to initialize: {e}")
            if self.debug:
                console.print_exception()
            return False
    
    async def _first_time_setup(self) -> Optional[Settings]:
        """
        Handle first-time setup process.
        
        Returns:
            Settings object if setup successful, None otherwise
        """
        try:
            console.print("\n🔧 [bold cyan]GerdsenAI CLI Setup[/bold cyan]\n")
            
            # Get LLM server URL
            default_url = "http://localhost:11434"
            llm_url = Prompt.ask(
                "Enter your local LLM server URL",
                default=default_url,
                console=console
            )
            
            # Test connection to LLM server
            show_info("Testing connection to LLM server...")
            
            temp_client = LLMClient(Settings(llm_server_url=llm_url))
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
                llm_server_url=llm_url,
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
        prompt_text.append("🤖 ", style="bright_cyan")
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
        Handle slash commands.
        
        Args:
            command: The command string starting with '/'
            
        Returns:
            True to continue running, False to exit
        """
        # TODO: Implement command parser and routing
        # For now, handle basic commands manually
        
        if command.strip() == '/exit' or command.strip() == '/quit':
            return False
        elif command.strip() == '/help':
            self._show_help()
        elif command.strip() == '/config':
            await self._show_config()
        elif command.strip() == '/models':
            await self._show_models()
        elif command.strip().startswith('/model '):
            await self._select_model(command.strip()[7:])
        elif command.strip() == '/status':
            await self._show_status()
        else:
            show_warning(f"Unknown command: {command}")
            show_info("Type /help to see available commands.")
        
        return True
    
    async def _handle_chat(self, message: str) -> bool:
        """
        Handle chat messages (non-command input).
        
        Args:
            message: The chat message
            
        Returns:
            True to continue running, False to exit
        """
        if not self.llm_client:
            show_error("LLM client not initialized")
            return True
        
        try:
            # Prepare chat messages
            messages = [
                ChatMessage(role="user", content=message)
            ]
            
            # Show thinking indicator
            with console.status("[bold green]Thinking...", spinner="dots"):
                response = await self.llm_client.chat(messages)
            
            if response:
                console.print("\n🤖 [bold cyan]Assistant[/bold cyan]:")
                console.print(response)
                console.print()
            else:
                show_error("Failed to get response from LLM")
                
        except Exception as e:
            show_error(f"Chat error: {e}")
            if self.debug:
                console.print_exception()
        
        return True
    
    def _show_help(self) -> None:
        """Display help information."""
        console.print("\n📚 [bold cyan]Available Commands[/bold cyan]\n")
        
        commands = [
            ("/help", "Show this help message"),
            ("/config", "Show current configuration"),
            ("/models", "List available models"),
            ("/model <name>", "Switch to a specific model"),
            ("/status", "Show system status"),
            ("/exit, /quit", "Exit the application"),
        ]
        
        for cmd, desc in commands:
            console.print(f"  [bold cyan]{cmd:15}[/bold cyan] {desc}")
        
        console.print("\n💬 [dim]Or just start typing to chat with your AI assistant![/dim]\n")
    
    async def _show_config(self) -> None:
        """Display current configuration."""
        if not self.settings:
            show_warning("No configuration loaded.")
            return
            
        console.print("\n⚙️  [bold cyan]Current Configuration[/bold cyan]\n")
        console.print(f"  LLM Server URL: [bold]{self.settings.llm_server_url}[/bold]")
        console.print(f"  Current Model:  [bold]{self.settings.current_model or 'Not set'}[/bold]")
        console.print(f"  API Timeout:    [bold]{self.settings.api_timeout}s[/bold]")
        
        # Show connection status
        if self.llm_client:
            status = "✅ Connected" if self.llm_client.is_connected else "❌ Disconnected"
            console.print(f"  Connection:     [bold]{status}[/bold]")
        
        console.print()
    
    async def _show_models(self) -> None:
        """Display available models."""
        if not self.llm_client:
            show_error("LLM client not initialized")
            return
        
        try:
            with console.status("[bold green]Loading models...", spinner="dots"):
                models = await self.llm_client.list_models()
            
            if not models:
                show_warning("No models available")
                return
            
            console.print("\n📋 [bold cyan]Available Models[/bold cyan]\n")
            
            for i, model in enumerate(models, 1):
                current = " [bold green]← current[/bold green]" if model.id == self.settings.current_model else ""
                console.print(f"  {i:2d}. [bold]{model.id}[/bold]{current}")
                if model.description:
                    console.print(f"      {model.description}", style="dim")
            
            console.print()
            
        except Exception as e:
            show_error(f"Failed to list models: {e}")
    
    async def _select_model(self, model_name: str) -> None:
        """Select a specific model."""
        if not self.llm_client:
            show_error("LLM client not initialized")
            return
        
        try:
            models = await self.llm_client.list_models()
            model_ids = [model.id for model in models]
            
            if model_name not in model_ids:
                show_error(f"Model '{model_name}' not found")
                show_info(f"Available models: {', '.join(model_ids)}")
                return
            
            # Update settings
            self.settings.current_model = model_name
            await self.config_manager.save_settings(self.settings)
            
            show_success(f"Switched to model: {model_name}")
            
        except Exception as e:
            show_error(f"Failed to select model: {e}")
    
    async def _show_status(self) -> None:
        """Display system status."""
        console.print("\n📊 [bold cyan]System Status[/bold cyan]\n")
        
        if self.llm_client:
            with console.status("[bold green]Checking status...", spinner="dots"):
                health = await self.llm_client.health_check()
            
            # Connection status
            status = "✅ Connected" if health["connected"] else "❌ Disconnected"
            console.print(f"  Connection:     [bold]{status}[/bold]")
            console.print(f"  Server URL:     [bold]{health['server_url']}[/bold]")
            
            if health["response_time_ms"]:
                console.print(f"  Response Time:  [bold]{health['response_time_ms']}ms[/bold]")
            
            console.print(f"  Models Found:   [bold]{health['models_available']}[/bold]")
            
            if health["error"]:
                console.print(f"  Error:          [bold red]{health['error']}[/bold red]")
        else:
            console.print("  LLM Client:     [bold red]Not initialized[/bold red]")
        
        console.print()
    
    async def run_async(self) -> None:
        """Run the async main loop."""
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
            console.print("\n👋 Goodbye!", style="bright_cyan")
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
