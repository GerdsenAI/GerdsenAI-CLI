"""Default tool registry wiring the agent's primitives into the tool loop.

`build_default_registry(agent)` exposes the agent's existing, battle-tested
primitives — project context, file editor, terminal — as `Tool`s the model can
call in the agentic loop. Read-only tools (read/search/analyze/semantic) run
freely; mutating tools (create/edit/run_command) are marked ``mutating`` so the
loop routes them through its async ``confirm`` gate. Crucially, the mutating
tools call the underlying primitives with their own interactive confirmation
**bypassed** (``apply_edit(force=True)`` / ``execute_command(require_confirmation
=False)``) — the loop's confirm callback is the single gate, so there's no
blocking ``Confirm.ask`` inside the async loop and no double-prompt.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from .file_editor import EditOperation
from .tool_registry import Tool, ToolRegistry

if TYPE_CHECKING:
    from .agent import Agent

logger = logging.getLogger(__name__)

_MAX_TOOL_RESULT_CHARS = 8000  # keep observations bounded for context budget


def _truncate(text: str, limit: int = _MAX_TOOL_RESULT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated {len(text) - limit} chars]"


def build_default_registry(agent: Agent) -> ToolRegistry:
    """Build the standard tool set bound to a live Agent."""
    reg = ToolRegistry()

    # -- read-only tools ------------------------------------------------- #

    async def read_file(path: str) -> str:
        content = await agent.context_manager.read_file_content(Path(path))
        if content is None:
            return f"Could not read file: {path}"
        agent._track_file_access(Path(path), "reading")
        return _truncate(f"# {path}\n{content}")

    async def search_files(query: str) -> str:
        files = agent.context_manager.get_relevant_files(query=query, max_files=10)
        if not files:
            return f"No files found matching: {query}"
        return "Relevant files:\n" + "\n".join(str(f.relative_path) for f in files)

    async def analyze_project() -> str:
        return _truncate(await agent._handle_project_analysis())

    async def semantic_search(query: str) -> str:
        result = await agent._retrieve_semantic_context(query)
        return result or "Semantic index unavailable or no matches."

    # -- mutating tools (gated by the loop's confirm callback) ----------- #

    async def create_file(path: str, content: str) -> str:
        edit = await agent.file_editor.propose_edit(
            Path(path), content, EditOperation.CREATE
        )
        if not edit:
            return f"Failed to propose creation of {path}."
        ok = await agent.file_editor.apply_edit(edit, force=True)
        if ok:
            agent.files_modified += 1
            return f"Created file: {path}"
        return f"Failed to create file: {path}"

    async def edit_file(path: str, new_content: str) -> str:
        edit = await agent.file_editor.propose_edit(
            Path(path), new_content, EditOperation.MODIFY
        )
        if not edit:
            return f"Failed to propose edit of {path}."
        ok = await agent.file_editor.apply_edit(edit, force=True)
        if ok:
            agent.files_modified += 1
            agent._track_file_access(Path(path), "editing")
            return f"Edited file: {path}"
        return f"Failed to edit file: {path}"

    async def run_command(command: str) -> str:
        # The loop's confirm gate already approved this; bypass the terminal's
        # own interactive prompt so the async loop never blocks on Confirm.ask.
        from .terminal import TerminalExecutor

        executor = getattr(agent, "terminal", None) or TerminalExecutor()
        result = await executor.execute_command(command, require_confirmation=False)
        parts = [f"$ {command}", f"exit_code={result.exit_code}"]
        if result.stdout:
            parts.append(_truncate(result.stdout))
        if result.stderr:
            parts.append("stderr:\n" + _truncate(result.stderr))
        return "\n".join(parts)

    reg.register(
        Tool(
            name="read_file",
            description="Read the full contents of a file in the project.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"}
                },
                "required": ["path"],
            },
            func=read_file,
        )
    )
    reg.register(
        Tool(
            name="search_files",
            description="Find files in the project relevant to a query.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for"}
                },
                "required": ["query"],
            },
            func=search_files,
        )
    )
    reg.register(
        Tool(
            name="analyze_project",
            description="Get an overview of the project structure and stats.",
            parameters={"type": "object", "properties": {}},
            func=analyze_project,
        )
    )
    reg.register(
        Tool(
            name="semantic_search",
            description=(
                "Semantic code search over the per-repo vector index "
                "(returns relevant snippets; empty if the index is unavailable)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural-language query"}
                },
                "required": ["query"],
            },
            func=semantic_search,
        )
    )
    reg.register(
        Tool(
            name="create_file",
            description="Create a new file with the given content.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
            func=create_file,
            mutating=True,
        )
    )
    reg.register(
        Tool(
            name="edit_file",
            description="Overwrite an existing file with new content.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "new_content": {"type": "string"},
                },
                "required": ["path", "new_content"],
            },
            func=edit_file,
            mutating=True,
        )
    )
    reg.register(
        Tool(
            name="run_command",
            description="Run a shell command in the project and return its output.",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command"}
                },
                "required": ["command"],
            },
            func=run_command,
            mutating=True,
        )
    )
    return reg
