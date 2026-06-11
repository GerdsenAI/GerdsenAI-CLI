"""The /delegate command: hand a sub-task to a fresh sub-agent loop.

Manual counterpart to the model-driven ``delegate`` tool. The whole argument
string is the task (no quoting needed), e.g. ``/delegate write unit tests for the
parser``. The sub-agent runs with the same tools and confirmation gates as the
main loop.
"""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel

from ..utils.display import show_warning
from .base import BaseCommand, CommandArgument, CommandCategory, CommandResult

console = Console()


class DelegateCommand(BaseCommand):
    """Run a focused sub-task in a fresh sub-agent loop."""

    @property
    def name(self) -> str:
        return "delegate"

    @property
    def description(self) -> str:
        return "Hand a focused sub-task to a fresh sub-agent and show its result"

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.AGENT

    @property
    def aliases(self) -> list[str]:
        return ["subagent"]

    def _define_arguments(self) -> dict[str, CommandArgument]:
        return {
            "task": CommandArgument(
                name="task",
                description="The self-contained sub-task to delegate",
                required=True,
            )
        }

    async def run(self, args_text: str, context: dict[str, Any]) -> CommandResult:
        """Treat the entire argument string as the task (no tokenization)."""
        task = (args_text or "").strip()
        if not task:
            return CommandResult(
                success=False, message=f"Usage: {self.usage}\n\n{self.description}"
            )
        return await self.execute({"task": task}, context)

    async def execute(
        self, args: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
        agent = context.get("agent")
        if agent is None:
            return CommandResult(success=False, message="Agent not initialized")

        from ..core.delegation import (
            delegation_enabled,
            delegation_max_depth,
            run_delegation,
        )

        if not delegation_enabled(agent):
            show_warning(
                "Delegation is disabled. Enable it with "
                "`/config set enable_delegation true`."
            )
            return CommandResult(success=False, message="Delegation disabled")

        task = args["task"]
        max_depth = delegation_max_depth(agent)
        with console.status("[bold cyan]Delegating to a sub-agent...", spinner="dots"):
            result = await run_delegation(agent, task, depth=1, max_depth=max_depth)

        console.print(Panel(result, title="🤝 Sub-agent result", border_style="cyan"))
        return CommandResult(
            success=True, message="Delegation complete", data={"result": result}
        )
