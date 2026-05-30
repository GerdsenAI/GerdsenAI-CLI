"""`/persona` — manage agent profiles bound to a provider + model."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table

from ..config.manager import ConfigManager
from ..core.agent_profiles import AgentProfile, AgentProfileManager
from .base import BaseCommand, CommandCategory, CommandResult

_ACTIONS = {"list", "current", "show", "add", "use", "remove", "system", "help"}


class PersonaCommand(BaseCommand):
    """Create, switch, and inspect agent personas (provider + model + prompt)."""

    @property
    def name(self) -> str:
        return "persona"

    @property
    def description(self) -> str:
        return "Bind named agent personas to a provider/model and switch between them"

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.AGENT

    @property
    def aliases(self) -> list[str]:
        return ["profile"]

    def parse_arguments(self, args_text: str) -> dict[str, Any]:
        text = args_text.strip()
        if not text:
            return {"action": "list", "rest": ""}
        parts = text.split(maxsplit=1)
        action = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""
        if action not in _ACTIONS:
            return {"action": "help", "rest": ""}
        return {"action": action, "rest": rest}

    def _manager(self, context: Any) -> AgentProfileManager:
        config = None
        if isinstance(context, dict):
            config = context.get("config_manager")
        return AgentProfileManager(
            config if isinstance(config, ConfigManager) else None
        )

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        console = Console()
        action = args.get("action", "list")
        rest = args.get("rest", "")
        mgr = self._manager(context)

        if action == "help":
            console.print(
                "[bold]/persona[/bold] — agent personas bound to a provider/model:\n"
                "  list                       list personas\n"
                "  current                    show the active persona\n"
                "  add <name> <model> [prov]  create a persona\n"
                "  system <name> <prompt...>  set a persona's system prompt\n"
                "  use <name>                 activate (switches the model too)\n"
                "  show <name>                show one persona\n"
                "  remove <name>              delete a persona"
            )
            return CommandResult(success=True)

        if action == "list":
            return self._list(console, mgr)
        if action == "current":
            return self._current(console, mgr)
        if action == "add":
            return self._add(console, mgr, rest)
        if action == "system":
            return self._set_system(console, mgr, rest)
        if action == "use":
            return self._use(console, mgr, rest, context)
        if action == "show":
            return self._show(console, mgr, rest)
        if action == "remove":
            return self._remove(console, mgr, rest)
        return CommandResult(success=False, message="Unknown action")

    # -- actions --------------------------------------------------------- #

    def _list(self, console: Console, mgr: AgentProfileManager) -> CommandResult:
        profiles = mgr.list()
        if not profiles:
            console.print(
                "[yellow]No personas yet.[/yellow] "
                "Create one: /persona add <name> <model> [provider]"
            )
            return CommandResult(success=True, message="No personas")
        active = mgr.get_active()
        active_name = active.name if active else ""
        table = Table(title="Agent Personas")
        table.add_column("", style="green")  # active marker
        table.add_column("Name", style="cyan")
        table.add_column("Model", style="white")
        table.add_column("Provider", style="magenta")
        table.add_column("Description", style="dim")
        for p in profiles:
            marker = "●" if p.name == active_name else ""
            table.add_row(marker, p.name, p.model, p.provider or "—", p.description)
        console.print(table)
        return CommandResult(success=True, message=f"{len(profiles)} persona(s)")

    def _current(self, console: Console, mgr: AgentProfileManager) -> CommandResult:
        active = mgr.get_active()
        if active is None:
            console.print("[dim]No active persona.[/dim]")
            return CommandResult(success=True, message="No active persona")
        console.print(
            f"[bold cyan]{active.name}[/bold cyan] "
            f"[dim](model={active.model}, provider={active.provider or '—'})[/dim]"
        )
        if active.system_prompt:
            console.print(active.system_prompt)
        return CommandResult(success=True, message=f"Active: {active.name}")

    def _add(
        self, console: Console, mgr: AgentProfileManager, rest: str
    ) -> CommandResult:
        tokens = rest.split()
        if len(tokens) < 2:
            console.print(
                "[yellow]Usage: /persona add <name> <model> [provider][/yellow]"
            )
            return CommandResult(success=False, message="Missing name/model")
        name, model = tokens[0], tokens[1]
        provider = tokens[2] if len(tokens) > 2 else ""
        profile = AgentProfile(name=name, model=model, provider=provider)
        if mgr.add(profile):
            console.print(
                f"[green]Created persona '{name}'[/green] "
                f"(model={model}, provider={provider or '—'}). "
                "Set its prompt with /persona system."
            )
            return CommandResult(success=True, message=f"Created {name}")
        return CommandResult(success=False, message="Failed to save persona")

    def _set_system(
        self, console: Console, mgr: AgentProfileManager, rest: str
    ) -> CommandResult:
        parts = rest.split(maxsplit=1)
        if len(parts) < 2:
            console.print("[yellow]Usage: /persona system <name> <prompt...>[/yellow]")
            return CommandResult(success=False, message="Missing prompt")
        name, prompt = parts[0], parts[1].strip()
        profile = mgr.get(name)
        if profile is None:
            console.print(f"[yellow]No persona named '{name}'.[/yellow]")
            return CommandResult(success=False, message="Not found")
        profile.system_prompt = prompt
        if mgr.add(profile):
            console.print(f"[green]Updated system prompt for '{name}'.[/green]")
            return CommandResult(success=True, message=f"Updated {name}")
        return CommandResult(success=False, message="Failed to save")

    def _use(
        self,
        console: Console,
        mgr: AgentProfileManager,
        rest: str,
        context: Any,
    ) -> CommandResult:
        name = rest.split()[0] if rest else ""
        if not name:
            console.print("[yellow]Usage: /persona use <name>[/yellow]")
            return CommandResult(success=False, message="Missing name")
        profile = mgr.set_active(name)
        if profile is None:
            console.print(f"[yellow]No persona named '{name}'.[/yellow]")
            return CommandResult(success=False, message="Not found")

        # Apply live to the running agent/settings if available.
        if isinstance(context, dict):
            agent = context.get("agent")
            if agent is not None and hasattr(agent, "persona_context"):
                agent.persona_context = profile.system_prompt
                if getattr(agent, "settings", None) is not None and profile.model:
                    agent.settings.current_model = profile.model

        console.print(
            f"[green]Activated persona '{profile.name}'[/green] "
            f"(model={profile.model})."
        )
        return CommandResult(success=True, message=f"Activated {profile.name}")

    def _show(
        self, console: Console, mgr: AgentProfileManager, rest: str
    ) -> CommandResult:
        name = rest.split()[0] if rest else ""
        profile = mgr.get(name) if name else None
        if profile is None:
            console.print(f"[yellow]No persona named '{name}'.[/yellow]")
            return CommandResult(success=False, message="Not found")
        console.print(
            f"[bold cyan]{profile.name}[/bold cyan]\n"
            f"  model:    {profile.model}\n"
            f"  provider: {profile.provider or '—'}\n"
            f"  prompt:   {profile.system_prompt or '(none)'}"
        )
        return CommandResult(success=True, message=f"Showed {profile.name}")

    def _remove(
        self, console: Console, mgr: AgentProfileManager, rest: str
    ) -> CommandResult:
        name = rest.split()[0] if rest else ""
        if mgr.remove(name):
            console.print(f"[green]Removed persona '{name}'.[/green]")
            return CommandResult(success=True, message=f"Removed {name}")
        console.print(f"[yellow]No persona named '{name}'.[/yellow]")
        return CommandResult(success=False, message="Not found")
