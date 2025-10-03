"""
File and session management commands for GerdsenAI CLI.

This module implements commands for direct file operations, session management,
and project file handling.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.table import Table

from ..config.manager import ConfigManager
from ..utils.helpers import format_size, get_file_type
from .base import BaseCommand, CommandArgument, CommandCategory, CommandResult


class FilesCommand(BaseCommand):
    """List files in the current project directory."""

    @property
    def name(self) -> str:
        """Command name."""
        return "ls"

    @property
    def description(self) -> str:
        """Brief description of the command."""
        return "List files in the current project directory"

    @property
    def category(self) -> CommandCategory:
        """Command category."""
        return CommandCategory.FILE

    @property
    def aliases(self) -> list[str]:
        """Alternative names for this command."""
        return ["list", "files", "listfiles"]

    def _define_arguments(self) -> dict[str, CommandArgument]:
        """Define command arguments."""
        return {
            "path": CommandArgument(
                name="path",
                description="Path to list (defaults to current directory)",
                required=False,
                arg_type=str,
                default=".",
            ),
            "--detailed": CommandArgument(
                name="--detailed",
                description="Show detailed file information",
                required=False,
                arg_type=bool,
                default=False,
            ),
            "--filter": CommandArgument(
                name="--filter",
                description="Filter files by extension or pattern",
                required=False,
                arg_type=str,
                default=None,
            ),
        }

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        """Execute the list files command."""
        console = Console()

        try:
            path = Path(args.get("path", "."))
            if not path.exists():
                console.print(f"[red]Path does not exist: {path}[/red]")
                return CommandResult(success=False, message="Path not found")

            if not path.is_dir():
                console.print(f"[red]Path is not a directory: {path}[/red]")
                return CommandResult(success=False, message="Not a directory")

            # Get files
            files = []
            for item in path.iterdir():
                if item.name.startswith("."):
                    continue  # Skip hidden files

                files.append(
                    {
                        "name": item.name,
                        "path": str(item),
                        "is_dir": item.is_dir(),
                        "size": item.stat().st_size if item.is_file() else 0,
                        "modified": datetime.fromtimestamp(item.stat().st_mtime),
                        "type": get_file_type(item.name)
                        if item.is_file()
                        else "directory",
                    }
                )

            # Apply filter
            filter_pattern = args.get("filter")
            if filter_pattern:
                files = [
                    f for f in files if filter_pattern.lower() in f["name"].lower()
                ]

            # Sort files (directories first, then by name)
            files.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

            if not files:
                console.print("[yellow]No files found.[/yellow]")
                return CommandResult(success=True, message="No files found")

            # Display files
            if args.get("detailed", False):
                await self._display_detailed_files(console, files, path)
            else:
                await self._display_simple_files(console, files, path)

            return CommandResult(
                success=True,
                message=f"Listed {len(files)} items",
                data={"files": files},
            )

        except Exception as e:
            error_msg = f"Failed to list files: {str(e)}"
            console.print(f"[red]Error: {error_msg}[/red]")
            return CommandResult(success=False, message=error_msg)

    async def _display_simple_files(
        self, console: Console, files: list[dict], path: Path
    ):
        """Display files in simple format."""
        table = Table(
            title=f"Files in {path}", show_header=True, header_style="bold cyan"
        )
        table.add_column("Name", style="white")
        table.add_column("Type", style="blue")
        table.add_column("Size", justify="right", style="green")

        for file_info in files:
            name = file_info["name"]
            if file_info["is_dir"]:
                name = f"📁 {name}"
                size_str = "---"
            else:
                name = f"📄 {name}"
                size_str = format_size(file_info["size"])

            table.add_row(name, file_info["type"], size_str)

        console.print(table)

    async def _display_detailed_files(
        self, console: Console, files: list[dict], path: Path
    ):
        """Display files with detailed information."""
        table = Table(
            title=f"Detailed Files in {path}",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Name", style="white")
        table.add_column("Type", style="blue")
        table.add_column("Size", justify="right", style="green")
        table.add_column("Modified", style="dim")
        table.add_column("Path", style="dim")

        for file_info in files:
            name = file_info["name"]
            if file_info["is_dir"]:
                name = f"📁 {name}"
                size_str = "---"
            else:
                name = f"📄 {name}"
                size_str = format_size(file_info["size"])

            modified_str = file_info["modified"].strftime("%Y-%m-%d %H:%M")

            table.add_row(
                name, file_info["type"], size_str, modified_str, file_info["path"]
            )

        console.print(table)


class ReadCommand(BaseCommand):
    """Read and display the contents of a file."""

    @property
    def name(self) -> str:
        """Command name."""
        return "cat"

    @property
    def description(self) -> str:
        """Brief description of the command."""
        return "Read and display the contents of a file"

    @property
    def category(self) -> CommandCategory:
        """Command category."""
        return CommandCategory.FILE

    @property
    def aliases(self) -> list[str]:
        """Alternative names for this command."""
        return ["read", "view", "readfile"]

    def _define_arguments(self) -> dict[str, CommandArgument]:
        """Define command arguments."""
        return {
            "file_path": CommandArgument(
                name="file_path",
                description="Path to the file to read",
                required=True,
                arg_type=str,
            ),
            "--lines": CommandArgument(
                name="--lines",
                description="Number of lines to display (0 for all)",
                required=False,
                arg_type=int,
                default=0,
            ),
            "--syntax": CommandArgument(
                name="--syntax",
                description="Force syntax highlighting language",
                required=False,
                arg_type=str,
                default=None,
            ),
        }

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        """Execute the read file command."""
        console = Console()

        try:
            file_path = Path(args["file_path"])

            if not file_path.exists():
                console.print(f"[red]File does not exist: {file_path}[/red]")
                return CommandResult(success=False, message="File not found")

            if not file_path.is_file():
                console.print(f"[red]Path is not a file: {file_path}[/red]")
                return CommandResult(success=False, message="Not a file")

            # Check file size
            file_size = file_path.stat().st_size
            if file_size > 1024 * 1024:  # 1MB limit
                if not Confirm.ask(
                    f"File is large ({format_size(file_size)}). Continue?"
                ):
                    return CommandResult(success=False, message="Operation cancelled")

            # Read file content
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                console.print("[red]Cannot read file: appears to be binary[/red]")
                return CommandResult(success=False, message="Binary file")

            # Apply line limit
            lines_limit = args.get("lines", 0)
            if lines_limit > 0:
                lines = content.split("\n")
                if len(lines) > lines_limit:
                    content = "\n".join(lines[:lines_limit])
                    console.print(
                        f"[dim]Showing first {lines_limit} lines of {len(lines)} total[/dim]"
                    )

            # Determine syntax highlighting
            syntax_lang = args.get("syntax") or get_file_type(file_path.name)

            # Display with syntax highlighting
            if content.strip():
                syntax = Syntax(
                    content, syntax_lang, theme="monokai", line_numbers=True
                )
                panel = Panel(syntax, title=f"📄 {file_path.name}", border_style="blue")
                console.print(panel)
            else:
                console.print(f"[dim]File {file_path.name} is empty[/dim]")

            return CommandResult(
                success=True,
                message=f"Read file: {file_path}",
                data={
                    "file_path": str(file_path),
                    "size": file_size,
                    "lines": len(content.split("\n")),
                },
            )

        except Exception as e:
            error_msg = f"Failed to read file: {str(e)}"
            console.print(f"[red]Error: {error_msg}[/red]")
            return CommandResult(success=False, message=error_msg)


class EditFileCommand(BaseCommand):
    """Edit a file with AI assistance."""

    @property
    def name(self) -> str:
        """Command name."""
        return "edit"

    @property
    def description(self) -> str:
        """Brief description of the command."""
        return "Edit a file with AI assistance"

    @property
    def category(self) -> CommandCategory:
        """Command category."""
        return CommandCategory.FILE

    @property
    def aliases(self) -> list[str]:
        """Alternative names for this command."""
        return ["modify", "change"]

    def _define_arguments(self) -> dict[str, CommandArgument]:
        """Define command arguments."""
        return {
            "file_path": CommandArgument(
                name="file_path",
                description="Path to the file to edit",
                required=True,
                arg_type=str,
            ),
            "instructions": CommandArgument(
                name="instructions",
                description="Instructions for the edit",
                required=True,
                arg_type=str,
            ),
            "--backup": CommandArgument(
                name="--backup",
                description="Create backup before editing",
                required=False,
                arg_type=bool,
                default=True,
            ),
        }

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        """Execute the edit file command."""
        console = Console()

        try:
            file_path = Path(args["file_path"])
            instructions = args.get("instructions")
            args.get("backup", True)

            if not file_path.exists():
                console.print(f"[red]File does not exist: {file_path}[/red]")
                return CommandResult(success=False, message="File not found")

            # Get agent and file editor from context
            agent = getattr(context, "agent", None) if context else None
            file_editor = getattr(context, "file_editor", None) if context else None

            if not agent or not file_editor:
                console.print("[red]Agent or file editor not available.[/red]")
                return CommandResult(
                    success=False, message="Required components not available"
                )

            console.print(f"[cyan]Editing file:[/cyan] {file_path}")
            console.print(f"[cyan]Instructions:[/cyan] {instructions}")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Processing edit request...", total=None)

                # Use agent to process the edit request
                result = await agent.process_file_edit(str(file_path), instructions)

                if result.get("success"):
                    progress.update(task, description="Edit completed successfully!")
                    console.print("[green]✓[/green] File edited successfully!")

                    if result.get("changes_applied"):
                        console.print(
                            f"[dim]Applied {len(result.get('changes', []))} changes[/dim]"
                        )
                else:
                    console.print(
                        f"[red]Edit failed: {result.get('error', 'Unknown error')}[/red]"
                    )
                    return CommandResult(
                        success=False, message=result.get("error", "Edit failed")
                    )

            return CommandResult(
                success=True,
                message=f"Successfully edited: {file_path}",
                data={
                    "file_path": str(file_path),
                    "changes": result.get("changes", []),
                },
            )

        except Exception as e:
            error_msg = f"Failed to edit file: {str(e)}"
            console.print(f"[red]Error: {error_msg}[/red]")
            return CommandResult(success=False, message=error_msg)


class CreateFileCommand(BaseCommand):
    """Create a new file with specified content."""

    @property
    def name(self) -> str:
        """Command name."""
        return "create"

    @property
    def description(self) -> str:
        """Brief description of the command."""
        return "Create a new file with specified content"

    @property
    def category(self) -> CommandCategory:
        """Command category."""
        return CommandCategory.FILE

    @property
    def aliases(self) -> list[str]:
        """Alternative names for this command."""
        return ["new", "make"]

    def _define_arguments(self) -> dict[str, CommandArgument]:
        """Define command arguments."""
        return {
            "file_path": CommandArgument(
                name="file_path",
                description="Path for the new file",
                required=True,
                arg_type=str,
            ),
            "content": CommandArgument(
                name="content",
                description="Content for the new file (or description for AI generation)",
                required=False,
                arg_type=str,
                default="",
            ),
            "--template": CommandArgument(
                name="--template",
                description="Use template for file creation",
                required=False,
                arg_type=str,
                default=None,
            ),
        }

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        """Execute the create file command."""
        console = Console()

        try:
            file_path = Path(args["file_path"])
            content = args.get("content", "")
            template = args.get("template")

            if file_path.exists():
                if not Confirm.ask(f"File {file_path} already exists. Overwrite?"):
                    return CommandResult(success=False, message="Operation cancelled")

            # Create directory if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Generate content based on template or use AI
            if template:
                content = self._get_template_content(template, file_path.name)
            elif content and not content.startswith("# "):
                # If content looks like instructions, use AI to generate
                agent = getattr(context, "agent", None) if context else None
                if agent:
                    console.print(f"[cyan]Generating content for:[/cyan] {file_path}")
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console,
                    ) as progress:
                        task = progress.add_task(
                            "Generating file content...", total=None
                        )
                        result = await agent.process_file_creation(
                            str(file_path), content
                        )

                        if result.get("success"):
                            content = result.get("content", content)
                            progress.update(task, description="Content generated!")
                        else:
                            console.print(
                                "[yellow]AI generation failed, using provided content[/yellow]"
                            )

            # Write file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # Display confirmation
            file_size = file_path.stat().st_size
            console.print(f"[green]✓[/green] Created file: {file_path}")
            console.print(
                f"[dim]Size: {format_size(file_size)}, Lines: {len(content.split(chr(10)))}[/dim]"
            )

            return CommandResult(
                success=True,
                message=f"Created file: {file_path}",
                data={"file_path": str(file_path), "size": file_size},
            )

        except Exception as e:
            error_msg = f"Failed to create file: {str(e)}"
            console.print(f"[red]Error: {error_msg}[/red]")
            return CommandResult(success=False, message=error_msg)

    def _get_template_content(self, template: str, filename: str) -> str:
        """Get content for a template type."""
        templates = {
            "python": f'''#!/usr/bin/env python3
"""
{filename} - Module description.
"""


def main():
    """Main function."""
    pass


if __name__ == "__main__":
    main()
''',
            "html": f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{filename.replace('.html', '').title()}</title>
</head>
<body>
    <h1>Welcome</h1>
    <p>This is a new HTML page.</p>
</body>
</html>
""",
            "markdown": f"""# {filename.replace('.md', '').replace('_', ' ').title()}

## Overview

This is a new Markdown document.

## Sections

- Section 1
- Section 2
- Section 3

## Conclusion

Summary and next steps.
""",
            "javascript": f"""/**
 * {filename} - Module description.
 */

function main() {{
    console.log("Hello from {filename}");
}}

// Export for modules
if (typeof module !== 'undefined' && module.exports) {{
    module.exports = {{ main }};
}}

// Run if called directly
if (require.main === module) {{
    main();
}}
""",
            "css": f"""/* {filename} - Stylesheet */

:root {{
    --primary-color: #007bff;
    --secondary-color: #6c757d;
    --background-color: #ffffff;
    --text-color: #333333;
}}

body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: var(--text-color);
    background-color: var(--background-color);
    margin: 0;
    padding: 0;
}}

.container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}}
""",
        }

        return templates.get(
            template.lower(),
            f"# {filename}\n\nNew file created with {template} template.\n",
        )


class SearchFilesCommand(BaseCommand):
    """Search for text patterns across project files."""

    @property
    def name(self) -> str:
        """Command name."""
        return "search"

    @property
    def description(self) -> str:
        """Brief description of the command."""
        return "Search for text patterns across project files"

    @property
    def category(self) -> CommandCategory:
        """Command category."""
        return CommandCategory.FILE

    @property
    def aliases(self) -> list[str]:
        """Alternative names for this command."""
        return ["grep", "find"]

    def _define_arguments(self) -> dict[str, CommandArgument]:
        """Define command arguments."""
        return {
            "pattern": CommandArgument(
                name="pattern",
                description="Text pattern to search for",
                required=True,
                arg_type=str,
            ),
            "--path": CommandArgument(
                name="--path",
                description="Directory to search in (defaults to current)",
                required=False,
                arg_type=str,
                default=".",
            ),
            "--extension": CommandArgument(
                name="--extension",
                description="File extension filter (e.g., .py, .js)",
                required=False,
                arg_type=str,
                default=None,
            ),
            "--limit": CommandArgument(
                name="--limit",
                description="Maximum number of results to show",
                required=False,
                arg_type=int,
                default=50,
            ),
        }

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        """Execute the search files command."""
        console = Console()

        try:
            pattern = args["pattern"]  # Required argument, use direct access
            search_path = Path(args.get("path", "."))
            extension_filter = args.get("extension")
            limit = args.get("limit", 50)

            if not search_path.exists():
                console.print(f"[red]Search path does not exist: {search_path}[/red]")
                return CommandResult(success=False, message="Search path not found")

            results = []

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Searching files...", total=None)

                # Search through files
                for file_path in search_path.rglob("*"):
                    if not file_path.is_file() or file_path.name.startswith("."):
                        continue

                    # Apply extension filter
                    if extension_filter and not file_path.name.endswith(
                        extension_filter
                    ):
                        continue

                    # Skip binary files
                    if get_file_type(file_path.name) in [
                        "binary",
                        "image",
                        "video",
                        "audio",
                    ]:
                        continue

                    try:
                        with open(file_path, encoding="utf-8") as f:
                            lines = f.readlines()

                        for line_num, line in enumerate(lines, 1):
                            if pattern.lower() in line.lower():
                                results.append(
                                    {
                                        "file": str(file_path),
                                        "line_num": line_num,
                                        "line": line.strip(),
                                        "context": self._get_context_lines(
                                            lines, line_num - 1, 2
                                        ),
                                    }
                                )

                                if len(results) >= limit:
                                    break

                    except (UnicodeDecodeError, PermissionError):
                        continue  # Skip files we can't read

                    if len(results) >= limit:
                        break

                progress.update(task, description=f"Found {len(results)} matches!")

            if not results:
                console.print(
                    f"[yellow]No matches found for pattern: {pattern}[/yellow]"
                )
                return CommandResult(success=True, message="No matches found")

            # Display results
            self._display_search_results(console, results, pattern, limit)

            return CommandResult(
                success=True,
                message=f"Found {len(results)} matches",
                data={"pattern": pattern, "results": results},
            )

        except Exception as e:
            error_msg = f"Search failed: {str(e)}"
            console.print(f"[red]Error: {error_msg}[/red]")
            return CommandResult(success=False, message=error_msg)

    def _get_context_lines(
        self, lines: list[str], target_line: int, context_size: int
    ) -> list[str]:
        """Get context lines around the target line."""
        start = max(0, target_line - context_size)
        end = min(len(lines), target_line + context_size + 1)
        return lines[start:end]

    def _display_search_results(
        self, console: Console, results: list[dict], pattern: str, limit: int
    ):
        """Display search results."""
        console.print(f"\n[bold]Search Results for '[cyan]{pattern}[/cyan]'[/bold]")

        if len(results) >= limit:
            console.print(
                f"[dim]Showing first {limit} results (more may exist)[/dim]\n"
            )

        current_file = None
        for result in results:
            file_path = result["file"]

            # Show file header if this is a new file
            if file_path != current_file:
                console.print(f"\n[bold blue]📄 {file_path}[/bold blue]")
                current_file = file_path

            # Show the match
            line_num = result["line_num"]
            line = result["line"]

            # Highlight the pattern in the line
            highlighted_line = (
                line.replace(pattern, f"[bold red]{pattern}[/bold red]")
                .replace(pattern.lower(), f"[bold red]{pattern.lower()}[/bold red]")
                .replace(pattern.upper(), f"[bold red]{pattern.upper()}[/bold red]")
            )

            console.print(f"  [dim]{line_num:4d}:[/dim] {highlighted_line}")


class SessionCommand(BaseCommand):
    """Manage work sessions and project state."""

    @property
    def name(self) -> str:
        """Command name."""
        return "session"

    @property
    def description(self) -> str:
        """Brief description of the command."""
        return "Manage work sessions and project state"

    @property
    def category(self) -> CommandCategory:
        """Command category."""
        return CommandCategory.SESSION

    @property
    def aliases(self) -> list[str]:
        """Alternative names for this command."""
        return ["sess"]

    def _define_arguments(self) -> dict[str, CommandArgument]:
        """Define command arguments."""
        return {
            "action": CommandArgument(
                name="action",
                description="Action: save, load, list, delete",
                required=True,
                arg_type=str,
            ),
            "name": CommandArgument(
                name="name",
                description="Session name for save/load/delete operations",
                required=False,
                arg_type=str,
                default=None,
            ),
        }

    async def execute(self, args: dict[str, Any], context: Any = None) -> CommandResult:
        """Execute the session command."""
        console = Console()
        action = args.get("action", "").lower()
        session_name = args.get("name")

        try:
            if action == "save":
                return await self._save_session(console, session_name, context)
            elif action == "load":
                return await self._load_session(console, session_name, context)
            elif action == "list":
                return await self._list_sessions(console, context)
            elif action == "delete":
                return await self._delete_session(console, session_name, context)
            else:
                console.print(f"[red]Unknown action: {action}[/red]")
                console.print("[dim]Available actions: save, load, list, delete[/dim]")
                return CommandResult(success=False, message=f"Unknown action: {action}")

        except Exception as e:
            error_msg = f"Session operation failed: {str(e)}"
            console.print(f"[red]Error: {error_msg}[/red]")
            return CommandResult(success=False, message=error_msg)

    async def _save_session(
        self, console: Console, session_name: str | None, context: Any
    ) -> CommandResult:
        """Save current session state."""
        if not session_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_name = f"session_{timestamp}"

        # Collect session data
        session_data = {
            "name": session_name,
            "timestamp": datetime.now().isoformat(),
            "conversation": [],
            "context_stats": {},
            "config": {},
        }

        # Get conversation history if agent available
        if context and hasattr(context, "agent"):
            session_data["conversation"] = context.agent.get_conversation_history()

        # Get context stats if context manager available
        if context and hasattr(context, "context_manager"):
            session_data["context_stats"] = context.context_manager.get_stats()

        # Get current config
        config = ConfigManager()
        session_data["config"] = {
            "current_model": config.get_setting("current_model"),
            "agent_settings": config.get_setting("agent", {}),
        }

        # Save to file
        sessions_dir = Path.home() / ".config" / "gerdsenai-cli" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        session_file = sessions_dir / f"{session_name}.json"
        with open(session_file, "w") as f:
            json.dump(session_data, f, indent=2, default=str)

        console.print(f"[green]✓[/green] Session saved: {session_name}")
        console.print(f"[dim]File: {session_file}[/dim]")

        return CommandResult(success=True, message=f"Session saved: {session_name}")

    async def _load_session(
        self, console: Console, session_name: str | None, context: Any
    ) -> CommandResult:
        """Load a saved session."""
        if not session_name:
            console.print("[red]Session name required for load operation.[/red]")
            return CommandResult(success=False, message="Session name required")

        sessions_dir = Path.home() / ".config" / "gerdsenai-cli" / "sessions"
        session_file = sessions_dir / f"{session_name}.json"

        if not session_file.exists():
            console.print(f"[red]Session not found: {session_name}[/red]")
            return CommandResult(success=False, message="Session not found")

        try:
            with open(session_file) as f:
                session_data = json.load(f)

            # Restore conversation if agent available
            if (
                context
                and hasattr(context, "agent")
                and session_data.get("conversation")
            ):
                context.agent.load_conversation_history(session_data["conversation"])

            # Restore config
            config = ConfigManager()
            if session_data.get("config"):
                for key, value in session_data["config"].items():
                    if key != "agent_settings":
                        config.update_setting(key, value)

                # Restore agent settings
                agent_settings = session_data["config"].get("agent_settings", {})
                for key, value in agent_settings.items():
                    config.update_setting(f"agent.{key}", value)

            console.print(f"[green]✓[/green] Session loaded: {session_name}")
            console.print(
                f"[dim]Timestamp: {session_data.get('timestamp', 'Unknown')}[/dim]"
            )

            return CommandResult(
                success=True, message=f"Session loaded: {session_name}"
            )

        except Exception as e:
            console.print(f"[red]Failed to load session: {e}[/red]")
            return CommandResult(success=False, message=f"Load failed: {e}")

    async def _list_sessions(self, console: Console, context: Any) -> CommandResult:
        """List all saved sessions."""
        sessions_dir = Path.home() / ".config" / "gerdsenai-cli" / "sessions"

        if not sessions_dir.exists():
            console.print("[yellow]No sessions directory found.[/yellow]")
            return CommandResult(success=True, message="No sessions found")

        session_files = list(sessions_dir.glob("*.json"))

        if not session_files:
            console.print("[yellow]No saved sessions found.[/yellow]")
            return CommandResult(success=True, message="No sessions found")

        table = Table(
            title="Saved Sessions", show_header=True, header_style="bold green"
        )
        table.add_column("Name", style="cyan")
        table.add_column("Date", style="white")
        table.add_column("Size", justify="right", style="dim")
        table.add_column("Conversations", justify="right", style="blue")

        for session_file in sorted(
            session_files, key=lambda x: x.stat().st_mtime, reverse=True
        ):
            name = session_file.stem
            size = format_size(session_file.stat().st_size)

            try:
                with open(session_file) as f:
                    session_data = json.load(f)
                timestamp = session_data.get("timestamp", "Unknown")
                conv_count = len(session_data.get("conversation", []))

                # Format timestamp
                if timestamp != "Unknown":
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        timestamp = dt.strftime("%Y-%m-%d %H:%M")
                    except (ValueError, TypeError):
                        pass

            except (FileNotFoundError, PermissionError, OSError):
                timestamp = "Unknown"
                conv_count = 0

            table.add_row(name, timestamp, size, str(conv_count))

        console.print(table)
        return CommandResult(
            success=True, message=f"Listed {len(session_files)} sessions"
        )

    async def _delete_session(
        self, console: Console, session_name: str | None, context: Any
    ) -> CommandResult:
        """Delete a saved session."""
        if not session_name:
            console.print("[red]Session name required for delete operation.[/red]")
            return CommandResult(success=False, message="Session name required")

        sessions_dir = Path.home() / ".config" / "gerdsenai-cli" / "sessions"
        session_file = sessions_dir / f"{session_name}.json"

        if not session_file.exists():
            console.print(f"[red]Session not found: {session_name}[/red]")
            return CommandResult(success=False, message="Session not found")

        if Confirm.ask(f"Delete session '{session_name}'?"):
            session_file.unlink()
            console.print(f"[green]✓[/green] Session deleted: {session_name}")
            return CommandResult(
                success=True, message=f"Session deleted: {session_name}"
            )
        else:
            return CommandResult(success=False, message="Operation cancelled")
