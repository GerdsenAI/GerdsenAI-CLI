"""`/discover` — find local and Tailscale LLM servers and optionally configure one."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlparse

from rich.console import Console
from rich.table import Table

from ..config.manager import ConfigManager
from ..config.settings import Settings
from ..core.providers.detector import DiscoveredProvider, ProviderDetector
from ..core.providers.tailscale import tailscale_available
from .base import BaseCommand, CommandArgument, CommandCategory, CommandResult


class DiscoverCommand(BaseCommand):
    """Scan localhost and the Tailscale tailnet for running LLM servers."""

    @property
    def name(self) -> str:
        return "discover"

    @property
    def description(self) -> str:
        return (
            "Auto-detect local and Tailscale LLM servers (Ollama, vLLM, LM Studio, TGI)"
        )

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.MODEL

    @property
    def aliases(self) -> list[str]:
        return ["scan", "find-models"]

    def _define_arguments(self) -> dict[str, CommandArgument]:
        return {
            "--no-tailscale": CommandArgument(
                name="--no-tailscale",
                description="Skip Tailscale peer discovery (scan localhost only)",
                required=False,
                arg_type=bool,
                default=False,
            ),
            "--configure": CommandArgument(
                name="--configure",
                description="Set the first discovered server as the active provider",
                required=False,
                arg_type=bool,
                default=False,
            ),
        }

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        console = Console()
        include_tailscale = not args.get("--no-tailscale", False)
        configure = args.get("--configure", False)

        detector = ProviderDetector()
        scope = "localhost"
        if include_tailscale and tailscale_available():
            scope = "localhost + Tailscale peers"
        console.print(f"[cyan]Scanning {scope} for LLM servers...[/cyan]")

        discovered = await detector.discover(include_tailscale=include_tailscale)

        if not discovered:
            console.print(
                "[yellow]No LLM servers found.[/yellow] "
                "Start one (e.g. `ollama serve`) and try again."
            )
            if include_tailscale and not tailscale_available():
                console.print(
                    "[dim]Tip: install Tailscale to discover models on other machines.[/dim]"
                )
            return CommandResult(success=True, message="No providers found")

        # Best-effort model listing for each discovered server.
        models_by_url = await self._list_models(discovered)
        self._render_table(console, discovered, models_by_url)

        message = f"Found {len(discovered)} provider(s)"
        if configure:
            chosen = discovered[0]
            ok = await self._configure(chosen)
            if ok:
                console.print(
                    f"\n[green]Configured active server:[/green] {chosen.url} "
                    f"({chosen.provider.get_provider_type().value})"
                )
                console.print(
                    "[dim]Use /models then /model <name> to pick a model.[/dim]"
                )
                message += f"; configured {chosen.url}"
            else:
                console.print("[red]Failed to save configuration.[/red]")

        return CommandResult(success=True, message=message)

    async def _list_models(
        self, discovered: list[DiscoveredProvider]
    ) -> dict[str, list[str]]:
        """Fetch model names per provider, best-effort (failures -> empty list)."""

        async def one(d: DiscoveredProvider) -> tuple[str, list[str]]:
            try:
                models = await d.provider.list_models()
                return d.url, [m.name for m in models]
            except Exception:
                return d.url, []

        results = await asyncio.gather(*(one(d) for d in discovered))
        return dict(results)

    def _render_table(
        self,
        console: Console,
        discovered: list[DiscoveredProvider],
        models_by_url: dict[str, list[str]],
    ) -> None:
        table = Table(title="Discovered LLM Servers")
        table.add_column("URL", style="cyan", no_wrap=True)
        table.add_column("Provider", style="green")
        table.add_column("Source", style="magenta")
        table.add_column("Models", style="white")

        for d in discovered:
            models = models_by_url.get(d.url, [])
            sample = ", ".join(models[:3])
            if len(models) > 3:
                sample += f", +{len(models) - 3} more"
            table.add_row(
                d.url,
                d.provider.get_provider_type().value,
                d.source,
                sample or "[dim]—[/dim]",
            )
        console.print(table)

    async def _configure(self, chosen: DiscoveredProvider) -> bool:
        """Persist the chosen server as the active provider."""
        config = ConfigManager()
        parsed = urlparse(chosen.url)
        data = config.get_settings().model_dump()
        data["protocol"] = parsed.scheme or "http"
        data["llm_host"] = parsed.hostname or "localhost"
        data["llm_port"] = parsed.port or 80
        data["llm_server_url"] = chosen.url
        try:
            new_settings = Settings(**data)
        except Exception:
            return False
        return await config.save_settings(new_settings)
