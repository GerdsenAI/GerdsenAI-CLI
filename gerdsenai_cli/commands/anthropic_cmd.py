"""`/anthropic` — manage and use the optional Anthropic (Claude) provider."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table

from ..config.manager import ConfigManager
from ..config.settings import Settings
from ..core import secrets
from ..core.providers.anthropic import AnthropicProvider
from .base import BaseCommand, CommandCategory, CommandResult

_ACTIONS = {"status", "set-key", "clear-key", "models", "model", "chat", "help"}


class AnthropicCommand(BaseCommand):
    """Configure the Anthropic API key/model and chat with Claude."""

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def description(self) -> str:
        return "Manage the Anthropic (Claude) provider: key, model, and chat"

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.MODEL

    @property
    def aliases(self) -> list[str]:
        return ["claude"]

    def parse_arguments(self, args_text: str) -> dict[str, Any]:
        text = args_text.strip()
        if not text:
            return {"action": "status", "value": ""}
        parts = text.split(maxsplit=1)
        action = parts[0].lower()
        value = parts[1].strip() if len(parts) > 1 else ""
        if action not in _ACTIONS:
            return {"action": "help", "value": ""}
        return {"action": action, "value": value}

    def _settings(self, context: Any) -> Settings:
        value = context.get("settings") if isinstance(context, dict) else None
        if isinstance(value, Settings):
            return value
        return ConfigManager().get_settings()

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        console = Console()
        action = args.get("action", "status")
        value = args.get("value", "")
        settings = self._settings(context)

        if action == "help":
            console.print(
                "[bold]/anthropic[/bold] commands:\n"
                "  status            show key source, model, SDK availability\n"
                "  set-key <key>     store the API key in the OS keyring\n"
                "  clear-key         remove the stored key\n"
                "  models            list available Claude models\n"
                "  model <name>      set the default Claude model\n"
                "  chat <message>    chat with Claude (streamed)"
            )
            return CommandResult(success=True)

        if action == "status":
            return self._status(console, settings)
        if action == "set-key":
            return self._set_key(console, value)
        if action == "clear-key":
            return self._clear_key(console)
        if action == "model":
            return self._set_model(console, value)
        if action == "models":
            return await self._models(console, settings)
        if action == "chat":
            return await self._chat(console, settings, value)

        return CommandResult(success=False, message="Unknown action")

    # -- actions --------------------------------------------------------- #

    def _status(self, console: Console, settings: Settings) -> CommandResult:
        try:
            import anthropic  # noqa: F401

            sdk = True
        except ImportError:
            sdk = False
        source = secrets.secret_source("anthropic") or "not set"
        console.print(
            "[bold]Anthropic provider[/bold]\n"
            f"  SDK installed:  {sdk}\n"
            f"  keyring:        {secrets.keyring_available()}\n"
            f"  API key source: {source}\n"
            f"  default model:  {settings.anthropic_model}"
        )
        if not sdk:
            console.print(
                r'[dim]Install with: pip install "gerdsenai-cli\[anthropic]"[/dim]'
            )
        return CommandResult(success=True, message="Anthropic status shown")

    def _set_key(self, console: Console, value: str) -> CommandResult:
        if not value:
            console.print("[yellow]Usage: /anthropic set-key <api-key>[/yellow]")
            return CommandResult(success=False, message="Missing key")
        if secrets.set_secret("anthropic", value):
            console.print("[green]API key stored in the OS keyring.[/green]")
            return CommandResult(success=True, message="Key stored")
        console.print(
            "[yellow]No keyring backend available. Set the ANTHROPIC_API_KEY "
            "environment variable instead (install the optional 'keyring' "
            "extra to store it securely).[/yellow]"
        )
        return CommandResult(success=False, message="Keyring unavailable")

    def _clear_key(self, console: Console) -> CommandResult:
        if secrets.delete_secret("anthropic"):
            console.print("[green]Stored API key removed from the keyring.[/green]")
            return CommandResult(success=True, message="Key cleared")
        console.print(
            "[yellow]No key removed (none stored, or no keyring backend).[/yellow]"
        )
        return CommandResult(success=True, message="Nothing to clear")

    def _set_model(self, console: Console, value: str) -> CommandResult:
        if not value:
            console.print("[yellow]Usage: /anthropic model <name>[/yellow]")
            return CommandResult(success=False, message="Missing model")
        ok = ConfigManager().update_setting("anthropic_model", value)
        if ok:
            console.print(f"[green]Default Claude model set to {value}.[/green]")
            return CommandResult(success=True, message=f"Model set to {value}")
        return CommandResult(success=False, message="Failed to save model")

    async def _models(self, console: Console, settings: Settings) -> CommandResult:
        provider = AnthropicProvider(model=settings.anthropic_model)
        if not await provider.detect():
            console.print(f"[yellow]{_unavailable()}[/yellow]")
            return CommandResult(success=True, message="Anthropic unavailable")
        models = await provider.list_models()
        table = Table(title="Anthropic Models")
        table.add_column("Model", style="cyan")
        table.add_column("Context", style="white", justify="right")
        for m in models:
            ctx = f"{m.context_length:,}" if m.context_length else "—"
            table.add_row(m.name, ctx)
        console.print(table)
        return CommandResult(success=True, message=f"{len(models)} model(s)")

    async def _chat(
        self, console: Console, settings: Settings, message: str
    ) -> CommandResult:
        if not message:
            console.print("[yellow]Usage: /anthropic chat <message>[/yellow]")
            return CommandResult(success=False, message="Missing message")
        provider = AnthropicProvider(model=settings.anthropic_model)
        if not await provider.detect():
            console.print(f"[yellow]{_unavailable()}[/yellow]")
            return CommandResult(success=True, message="Anthropic unavailable")

        console.print(f"[bold cyan]Claude ({settings.anthropic_model})[/bold cyan]:")
        try:
            async for chunk in provider.stream_completion(
                messages=[{"role": "user", "content": message}],
                model=settings.anthropic_model,
            ):
                console.print(chunk, end="")
            console.print()
        except Exception as e:
            console.print(f"\n[red]Anthropic error: {e}[/red]")
            return CommandResult(success=False, message=str(e))
        return CommandResult(success=True, message="Claude responded")


def _unavailable() -> str:
    return (
        "Anthropic is unavailable. Install the SDK "
        r'(pip install "gerdsenai-cli\[anthropic]") and set a key with '
        "/anthropic set-key <key> (or ANTHROPIC_API_KEY)."
    )
