"""
Model management commands for GerdsenAI CLI.

This module implements commands for managing LLM models, including switching models,
listing available models, and configuring model settings.
"""

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..config.manager import ConfigManager
from ..core.llm_client import LLMClient
from ..utils.helpers import format_duration, format_size
from .base import BaseCommand, CommandArgument, CommandCategory, CommandResult


class ListModelsCommand(BaseCommand):
    """List all available models from the LLM server."""

    name = "models"
    description = "List all available models from the LLM server"
    category = CommandCategory.MODEL
    aliases = ["list-models", "model-list"]

    arguments = [
        CommandArgument(
            name="--detailed",
            description="Show detailed model information",
            required=False,
            arg_type=bool,
            default=False,
        ),
        CommandArgument(
            name="--filter",
            description="Filter models by name pattern",
            required=False,
            arg_type=str,
            default=None,
        ),
    ]

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        """Execute the list models command."""
        console = Console()

        try:
            # Get LLM client from context
            llm_client = getattr(context, "llm_client", None) if context else None
            if not llm_client:
                config = ConfigManager()
                llm_client = LLMClient(config.get_settings())

            # Connect and list models
            await llm_client.connect()
            models = await llm_client.list_models()

            if not models:
                console.print("[yellow]No models found on the server.[/yellow]")
                return CommandResult(success=True, message="No models available")

            # Apply filter if specified
            filter_pattern = args.get("filter")
            if filter_pattern:
                models = [
                    m
                    for m in models
                    if filter_pattern.lower() in m.get("name", "").lower()
                ]
                if not models:
                    console.print(
                        f"[yellow]No models found matching pattern: {filter_pattern}[/yellow]"
                    )
                    return CommandResult(
                        success=True, message=f"No models matching '{filter_pattern}'"
                    )

            # Display models
            if args.get("detailed", False):
                await self._display_detailed_models(console, models, context)
            else:
                await self._display_simple_models(console, models, context)

            return CommandResult(
                success=True,
                message=f"Listed {len(models)} models",
                data={"models": models},
            )

        except Exception as e:
            error_msg = f"Failed to list models: {str(e)}"
            console.print(f"[red]Error: {error_msg}[/red]")
            return CommandResult(success=False, message=error_msg)

    async def _display_simple_models(
        self, console: Console, models: list[dict], context: Any
    ):
        """Display models in simple table format."""
        config = ConfigManager()
        current_model = config.get_setting("current_model", "")

        table = Table(
            title="Available Models", show_header=True, header_style="bold magenta"
        )
        table.add_column("Model Name", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Size", justify="right")

        for model in models:
            name = model.get("name", "Unknown")
            size = model.get("size", 0)
            status = "🟢 Current" if name == current_model else "⚪ Available"

            table.add_row(name, status, format_size(size) if size else "Unknown")

        console.print(table)

    async def _display_detailed_models(
        self, console: Console, models: list[dict], context: Any
    ):
        """Display models with detailed information."""
        config = ConfigManager()
        current_model = config.get_setting("current_model", "")

        for i, model in enumerate(models):
            name = model.get("name", "Unknown")
            is_current = name == current_model

            # Create panel content
            details = []

            # Basic info
            details.append(f"[bold]Name:[/bold] {name}")
            details.append(
                f"[bold]Status:[/bold] {'🟢 Currently Active' if is_current else '⚪ Available'}"
            )

            # Size info
            size = model.get("size", 0)
            if size:
                details.append(f"[bold]Size:[/bold] {format_size(size)}")

            # Model details
            if "digest" in model:
                details.append(f"[bold]Digest:[/bold] {model['digest'][:16]}...")

            if "modified_at" in model:
                details.append(f"[bold]Modified:[/bold] {model['modified_at']}")

            if "details" in model:
                model_details = model["details"]
                if "family" in model_details:
                    details.append(f"[bold]Family:[/bold] {model_details['family']}")
                if "parameter_size" in model_details:
                    details.append(
                        f"[bold]Parameters:[/bold] {model_details['parameter_size']}"
                    )
                if "quantization_level" in model_details:
                    details.append(
                        f"[bold]Quantization:[/bold] {model_details['quantization_level']}"
                    )

            panel_style = "green" if is_current else "blue"
            panel = Panel(
                "\n".join(details),
                title=f"Model {i+1}/{len(models)}",
                border_style=panel_style,
            )
            console.print(panel)

            if i < len(models) - 1:
                console.print()


class SwitchModelCommand(BaseCommand):
    """Switch to a different model."""

    name = "model"
    description = "Switch to a specific model"
    category = CommandCategory.MODEL
    aliases = ["switch-model", "use-model"]

    arguments = [
        CommandArgument(
            name="model_name",
            description="Name of the model to switch to",
            required=True,
            arg_type=str,
        ),
        CommandArgument(
            name="--force",
            description="Force switch without validation",
            required=False,
            arg_type=bool,
            default=False,
        ),
    ]

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        """Execute the switch model command."""
        console = Console()
        model_name = args.get("model_name")
        force = args.get("force", False)

        try:
            config = ConfigManager()
            current_model = config.get_setting("current_model", "")

            if model_name == current_model:
                console.print(f"[yellow]Already using model: {model_name}[/yellow]")
                return CommandResult(
                    success=True, message=f"Already using {model_name}"
                )

            # Validate model exists unless forced
            if not force:
                llm_client = getattr(context, "llm_client", None) if context else None
                if not llm_client:
                    llm_client = LLMClient(config.get_settings())

                await llm_client.connect()
                models = await llm_client.list_models()
                model_names = [m.get("name", "") for m in models]

                if model_name not in model_names:
                    console.print(
                        f"[red]Model '{model_name}' not found on server.[/red]"
                    )
                    console.print(
                        f"[dim]Available models: {', '.join(model_names)}[/dim]"
                    )
                    return CommandResult(
                        success=False, message=f"Model '{model_name}' not found"
                    )

            # Switch model
            old_model = current_model
            config.update_setting("current_model", model_name)

            # Update LLM client if available in context
            if context and hasattr(context, "llm_client"):
                context.llm_client.settings.current_model = model_name

            console.print(
                f"[green]✓[/green] Switched from [cyan]{old_model or 'none'}[/cyan] to [cyan]{model_name}[/cyan]"
            )

            return CommandResult(
                success=True,
                message=f"Switched to model: {model_name}",
                data={"old_model": old_model, "new_model": model_name},
            )

        except Exception as e:
            error_msg = f"Failed to switch model: {str(e)}"
            console.print(f"[red]Error: {error_msg}[/red]")
            return CommandResult(success=False, message=error_msg)


class ModelInfoCommand(BaseCommand):
    """Get detailed information about a specific model."""

    name = "model-info"
    description = "Get detailed information about a specific model"
    category = CommandCategory.MODEL
    aliases = ["describe-model", "minfo"]

    arguments = [
        CommandArgument(
            name="model_name",
            description="Name of the model to get info about (defaults to current model)",
            required=False,
            arg_type=str,
            default=None,
        )
    ]

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        """Execute the model info command."""
        console = Console()

        try:
            config = ConfigManager()
            model_name = args.get("model_name") or config.get_setting(
                "current_model", ""
            )

            if not model_name:
                console.print("[red]No model specified and no current model set.[/red]")
                return CommandResult(success=False, message="No model specified")

            # Get LLM client
            llm_client = getattr(context, "llm_client", None) if context else None
            if not llm_client:
                llm_client = LLMClient(config.get_settings())

            await llm_client.connect()
            models = await llm_client.list_models()

            # Find the specific model
            target_model = None
            for model in models:
                if model.get("name") == model_name:
                    target_model = model
                    break

            if not target_model:
                console.print(f"[red]Model '{model_name}' not found on server.[/red]")
                return CommandResult(
                    success=False, message=f"Model '{model_name}' not found"
                )

            # Display detailed model information
            await self._display_model_info(console, target_model, config)

            return CommandResult(
                success=True,
                message=f"Displayed info for model: {model_name}",
                data={"model": target_model},
            )

        except Exception as e:
            error_msg = f"Failed to get model info: {str(e)}"
            console.print(f"[red]Error: {error_msg}[/red]")
            return CommandResult(success=False, message=error_msg)

    async def _display_model_info(
        self, console: Console, model: dict, config: ConfigManager
    ):
        """Display detailed information about a model."""
        name = model.get("name", "Unknown")
        is_current = name == config.get_setting("current_model", "")

        # Create main info section
        info_lines = []

        # Header
        status_icon = "🟢" if is_current else "⚪"
        info_lines.append(f"[bold cyan]{name}[/bold cyan] {status_icon}")
        info_lines.append("")

        # Basic information
        info_lines.append("[bold]Basic Information:[/bold]")
        info_lines.append(
            f"  Status: {'Currently Active' if is_current else 'Available'}"
        )

        size = model.get("size", 0)
        if size:
            info_lines.append(f"  Size: {format_size(size)}")

        if "digest" in model:
            info_lines.append(f"  Digest: {model['digest']}")

        if "modified_at" in model:
            info_lines.append(f"  Modified: {model['modified_at']}")

        # Model details
        if "details" in model:
            details = model["details"]
            info_lines.append("")
            info_lines.append("[bold]Model Details:[/bold]")

            if "family" in details:
                info_lines.append(f"  Family: {details['family']}")
            if "format" in details:
                info_lines.append(f"  Format: {details['format']}")
            if "parameter_size" in details:
                info_lines.append(f"  Parameters: {details['parameter_size']}")
            if "quantization_level" in details:
                info_lines.append(f"  Quantization: {details['quantization_level']}")
            if "families" in details:
                info_lines.append(f"  Families: {', '.join(details['families'])}")

        # Model file information
        if "model_info" in model:
            model_info = model["model_info"]
            info_lines.append("")
            info_lines.append("[bold]Model File Info:[/bold]")

            for key, value in model_info.items():
                if key not in ["general.architecture"]:  # Skip technical fields
                    formatted_key = key.replace("_", " ").title()
                    info_lines.append(f"  {formatted_key}: {value}")

        panel = Panel(
            "\n".join(info_lines),
            title="Model Information",
            border_style="green" if is_current else "blue",
            padding=(1, 2),
        )
        console.print(panel)


class ModelStatsCommand(BaseCommand):
    """Show statistics about model usage and performance."""

    name = "model-stats"
    description = "Show statistics about model usage and performance"
    category = CommandCategory.MODEL
    aliases = ["stats", "model-performance"]

    arguments = [
        CommandArgument(
            name="--reset",
            description="Reset statistics",
            required=False,
            arg_type=bool,
            default=False,
        )
    ]

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        """Execute the model stats command."""
        console = Console()

        try:
            config = ConfigManager()

            if args.get("reset", False):
                # Reset statistics
                config.update_setting("model_stats", {})
                console.print("[green]✓[/green] Model statistics reset.")
                return CommandResult(success=True, message="Statistics reset")

            # Get current stats
            stats = config.get_setting("model_stats", {})
            current_model = config.get_setting("current_model", "")

            if not stats:
                console.print("[yellow]No model statistics available yet.[/yellow]")
                console.print(
                    "[dim]Statistics will be collected as you use models.[/dim]"
                )
                return CommandResult(success=True, message="No statistics available")

            # Display statistics
            table = Table(
                title="Model Usage Statistics",
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Model", style="cyan")
            table.add_column("Requests", justify="right")
            table.add_column("Total Tokens", justify="right")
            table.add_column("Avg Response Time", justify="right")
            table.add_column("Last Used", style="dim")

            for model_name, model_stats in stats.items():
                requests = model_stats.get("requests", 0)
                tokens = model_stats.get("total_tokens", 0)
                avg_time = model_stats.get("avg_response_time", 0)
                last_used = model_stats.get("last_used", "Never")

                status_indicator = "🟢 " if model_name == current_model else ""

                table.add_row(
                    f"{status_indicator}{model_name}",
                    str(requests),
                    f"{tokens:,}",
                    format_duration(avg_time) if avg_time else "N/A",
                    last_used,
                )

            console.print(table)

            # Summary
            total_requests = sum(stats.get(m, {}).get("requests", 0) for m in stats)
            total_tokens = sum(stats.get(m, {}).get("total_tokens", 0) for m in stats)

            summary = f"\n[bold]Summary:[/bold] {len(stats)} models used, {total_requests:,} total requests, {total_tokens:,} total tokens"
            console.print(summary)

            return CommandResult(
                success=True,
                message=f"Displayed statistics for {len(stats)} models",
                data={"stats": stats},
            )

        except Exception as e:
            error_msg = f"Failed to display model stats: {str(e)}"
            console.print(f"[red]Error: {error_msg}[/red]")
            return CommandResult(success=False, message=error_msg)
