"""Slash commands for imported skills / agent files.

``SkillCommand`` wraps a single discovered skill so it can be invoked directly
(``/<skill-name>``), printing its instructions. ``SkillsCommand`` lists and shows
all discovered skills.
"""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from ..core.skill_loader import Skill, discover_skills
from .base import BaseCommand, CommandCategory, CommandResult


class SkillCommand(BaseCommand):
    """Invoke a single imported skill (prints its instructions)."""

    def __init__(self, skill: Skill) -> None:
        super().__init__()
        self._skill = skill

    @property
    def name(self) -> str:
        return self._skill.command_name

    @property
    def description(self) -> str:
        return f"[skill] {self._skill.description}"

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.AGENT

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        console = Console()
        console.print(
            f"[bold cyan]{self._skill.name}[/bold cyan] "
            f"[dim]({self._skill.kind} · {self._skill.source})[/dim]"
        )
        if self._skill.body:
            console.print(Markdown(self._skill.body))
        return CommandResult(
            success=True,
            message=f"Loaded skill: {self._skill.name}",
            data={"skill": self._skill.name, "body": self._skill.body},
        )


class SkillsCommand(BaseCommand):
    """List and show imported skills / agent files."""

    def __init__(self, skills: list[Skill] | None = None) -> None:
        super().__init__()
        self._skills = skills if skills is not None else discover_skills()

    @property
    def name(self) -> str:
        return "skills"

    @property
    def description(self) -> str:
        return "List imported skills/agent files (Claude skills, AGENTS.md, subagents)"

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.AGENT

    @property
    def aliases(self) -> list[str]:
        return ["agents"]

    def parse_arguments(self, args_text: str) -> dict[str, Any]:
        text = args_text.strip()
        if not text:
            return {"action": "list", "name": ""}
        parts = text.split(maxsplit=1)
        if parts[0].lower() in {"list", "show", "reload"}:
            return {
                "action": parts[0].lower(),
                "name": parts[1].strip() if len(parts) > 1 else "",
            }
        # Bare argument is treated as: show <name>.
        return {"action": "show", "name": text}

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        console = Console()
        action = args.get("action", "list")
        name = args.get("name", "")

        if action == "reload":
            self._skills = discover_skills()
            console.print(f"[green]Reloaded {len(self._skills)} skill(s).[/green]")
            return CommandResult(success=True, message="Skills reloaded")

        if not self._skills:
            console.print(
                "[yellow]No imported skills found.[/yellow] "
                "Add .claude/skills/<name>/SKILL.md, .claude/agents/*.md, or AGENTS.md."
            )
            return CommandResult(success=True, message="No skills")

        if action == "show":
            match = next(
                (s for s in self._skills if s.command_name == name or s.name == name),
                None,
            )
            if match is None:
                console.print(f"[yellow]No skill named '{name}'.[/yellow]")
                return CommandResult(success=False, message="Skill not found")
            console.print(
                f"[bold cyan]{match.name}[/bold cyan] [dim]({match.kind})[/dim]"
            )
            console.print(Markdown(match.body or "_(no content)_"))
            return CommandResult(success=True, message=f"Showed {match.name}")

        # default: list
        table = Table(title="Imported Skills & Agents")
        table.add_column("Command", style="cyan")
        table.add_column("Kind", style="magenta")
        table.add_column("Description", style="white")
        for skill in self._skills:
            table.add_row(f"/{skill.command_name}", skill.kind, skill.description)
        console.print(table)
        console.print("[dim]Use /skills show <name> to view a skill's full text.[/dim]")
        return CommandResult(success=True, message=f"{len(self._skills)} skill(s)")
