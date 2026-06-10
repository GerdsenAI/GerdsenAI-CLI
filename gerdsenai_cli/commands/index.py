"""`/index` — build and query a per-repo semantic (vector) index."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from ..config.manager import ConfigManager
from ..config.settings import Settings
from ..core.repo_index import build_indexer
from .base import BaseCommand, CommandArgument, CommandCategory, CommandResult

_ACTIONS = {"build", "refresh", "update", "status", "search", "clear", "help"}
_UNAVAILABLE = (
    "Vector indexing is unavailable. Ensure Qdrant is running "
    "(default http://localhost:6333) and an embedding backend exists "
    "(pull an Ollama embed model, e.g. `ollama pull nomic-embed-text`, "
    "or install the optional `sentence-transformers` extra)."
)


class IndexCommand(BaseCommand):
    """Manage the repository's vector index for semantic code search."""

    @property
    def name(self) -> str:
        return "index"

    @property
    def description(self) -> str:
        return "Build/search a per-repo semantic index (Qdrant + local embeddings)"

    @property
    def category(self) -> CommandCategory:
        return CommandCategory.CONTEXT

    @property
    def aliases(self) -> list[str]:
        return ["vector-index"]

    def _define_arguments(self) -> dict[str, CommandArgument]:
        # Documented for /help; actual parsing is custom (see parse_arguments).
        return {
            "action": CommandArgument(
                name="action",
                description=(
                    "build | refresh | update | status | search <query> | clear"
                ),
                required=False,
                default="status",
                choices=sorted(_ACTIONS),
            ),
        }

    def parse_arguments(self, args_text: str) -> dict[str, Any]:
        """Custom parse: first token is the action, the rest is a free-text query."""
        text = args_text.strip()
        if not text:
            return {"action": "status", "query": ""}
        parts = text.split(maxsplit=1)
        action = parts[0].lower()
        query = parts[1].strip() if len(parts) > 1 else ""
        if action not in _ACTIONS:
            # Treat a bare query as: search <everything>.
            return {"action": "search", "query": text}
        return {"action": action, "query": query}

    def _settings(self, context: Any) -> Settings:
        value = context.get("settings") if isinstance(context, dict) else None
        if isinstance(value, Settings):
            return value
        return ConfigManager().get_settings()

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        console = Console()
        action = args.get("action", "status")
        query = args.get("query", "")

        if action == "help":
            console.print(self.help_text)
            return CommandResult(success=True)

        settings = self._settings(context)
        repo_root = Path.cwd()
        indexer = await build_indexer(settings, repo_root)

        if indexer is None:
            console.print(f"[yellow]{_UNAVAILABLE}[/yellow]")
            return CommandResult(success=True, message="Vector indexing unavailable")

        try:
            if action == "build":
                console.print(
                    f"[cyan]Indexing repository into '{indexer.collection}'...[/cyan]"
                )
                stats = await indexer.build()
                console.print(
                    f"[green]Indexed {stats.chunks} chunks from {stats.files} "
                    f"files[/green] ({stats.skipped} skipped)"
                )
                for err in stats.errors:
                    console.print(f"[red]  {err}[/red]")
                return CommandResult(
                    success=True, message=f"Indexed {stats.chunks} chunks"
                )

            if action in {"refresh", "update"}:
                console.print(
                    f"[cyan]Refreshing changed files in "
                    f"'{indexer.collection}'...[/cyan]"
                )
                stats = await indexer.build_incremental()
                console.print(
                    f"[green]Re-indexed {stats.chunks} chunks from {stats.files} "
                    f"changed file(s)[/green] "
                    f"({stats.unchanged} unchanged, {stats.removed} removed)"
                )
                for err in stats.errors:
                    console.print(f"[red]  {err}[/red]")
                return CommandResult(
                    success=True,
                    message=f"Refreshed {stats.files} changed file(s)",
                )

            if action == "clear":
                await indexer.clear()
                console.print("[green]Index cleared.[/green]")
                return CommandResult(success=True, message="Index cleared")

            if action == "search":
                if not query:
                    console.print("[yellow]Usage: /index search <query>[/yellow]")
                    return CommandResult(success=False, message="Missing query")
                hits = await indexer.search(query, limit=5)
                if not hits:
                    console.print(
                        "[yellow]No results. Run /index build first if you "
                        "haven't.[/yellow]"
                    )
                    return CommandResult(success=True, message="No results")
                table = Table(title=f"Semantic search: {query}")
                table.add_column("Score", style="cyan", justify="right")
                table.add_column("Location", style="green")
                table.add_column("Snippet", style="white")
                for hit in hits:
                    p = hit.payload
                    loc = f"{p.get('path', '?')}:{p.get('start_line', '?')}"
                    snippet = str(p.get("text", "")).strip().replace("\n", " ")[:80]
                    table.add_row(f"{hit.score:.3f}", loc, snippet)
                console.print(table)
                return CommandResult(success=True, message=f"{len(hits)} result(s)")

            # default: status
            status = await indexer.status()
            console.print(
                f"[bold]Vector index[/bold]\n"
                f"  collection: {status['collection']}\n"
                f"  exists:     {status['exists']}\n"
                f"  points:     {status['points']}\n"
                f"  backend:    {status['backend']}"
            )
            return CommandResult(success=True, message="Index status shown")
        finally:
            await indexer.aclose()
