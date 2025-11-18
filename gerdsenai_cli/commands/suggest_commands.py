"""
Suggestion command implementation for GerdsenAI CLI.

Provides /suggest command for proactive code improvement suggestions.
"""

import logging
from pathlib import Path

from .base import BaseCommand, CommandCategory

logger = logging.getLogger(__name__)


class SuggestCommand(BaseCommand):
    """Command for generating proactive suggestions."""

    name = "suggest"
    description = "Generate proactive suggestions for code improvements"
    category = CommandCategory.AGENT
    usage = "/suggest [file|project|task <description>]"

    async def execute(self, args: list[str]) -> str:
        """
        Execute suggest command.

        Args:
            args: Command arguments

        Returns:
            Result message
        """
        if not hasattr(self.agent, "suggestor"):
            return "Error: Suggestion system not initialized"

        suggestor = self.agent.suggestor

        # Parse subcommand
        if not args:
            # Default: show help
            return self._show_help()

        subcommand = args[0]

        if subcommand == "file":
            # Suggest for specific file
            if len(args) < 2:
                return "Usage: /suggest file <path>"
            return await self._suggest_for_file(args[1], suggestor)

        elif subcommand == "project":
            # Suggest for entire project
            return await self._suggest_for_project(suggestor)

        elif subcommand == "task":
            # Suggest for task description
            if len(args) < 2:
                return "Usage: /suggest task <description>"
            task_description = " ".join(args[1:])
            return await self._suggest_for_task(task_description, suggestor)

        elif subcommand == "help":
            return self._show_help()

        else:
            # Treat entire input as task description
            task_description = " ".join(args)
            return await self._suggest_for_task(task_description, suggestor)

    async def _suggest_for_file(self, file_path: str, suggestor) -> str:
        """
        Generate suggestions for a specific file.

        Args:
            file_path: Path to file
            suggestor: ProactiveSuggestor instance

        Returns:
            Result message
        """
        try:
            path = Path(file_path)

            if not path.exists():
                return f"Error: File not found: {file_path}"

            # Read file content
            content = path.read_text()

            # Analyze file
            suggestions = suggestor.analyze_file(path, content)

            if not suggestions:
                return f"No suggestions for {file_path}"

            # Display suggestions
            if self.console:
                self.console.show_suggestion_details(suggestions)
                return ""
            else:
                return self._format_suggestions_text(suggestions)

        except Exception as e:
            logger.error(f"Failed to analyze file {file_path}: {e}", exc_info=True)
            return f"Error analyzing file: {e}"

    async def _suggest_for_project(self, suggestor) -> str:
        """
        Generate suggestions for entire project.

        Args:
            suggestor: ProactiveSuggestor instance

        Returns:
            Result message
        """
        try:
            # Get project files from agent's file manager
            if not hasattr(self.agent, "file_manager"):
                return "Error: File manager not available"

            # Get current working directory
            cwd = Path.cwd()

            # Find Python files
            python_files = list(cwd.rglob("*.py"))

            # Limit to reasonable number
            python_files = python_files[:20]

            all_suggestions = []

            for file_path in python_files:
                # Skip certain directories
                if any(
                    part in file_path.parts
                    for part in [".git", "__pycache__", "venv", ".venv"]
                ):
                    continue

                try:
                    content = file_path.read_text()
                    suggestions = suggestor.analyze_file(file_path, content)
                    all_suggestions.extend(suggestions)
                except Exception as e:
                    logger.warning(f"Failed to analyze {file_path}: {e}")

            # Also check project structure
            files_dict = {str(f): None for f in python_files}
            structure_suggestions = suggestor.analyze_project_structure(
                files_dict, {}
            )
            all_suggestions.extend(structure_suggestions)

            if not all_suggestions:
                return "No suggestions for this project"

            # Filter and prioritize
            filtered = suggestor.filter_suggestions(
                all_suggestions, max_count=10, min_priority="medium"
            )

            # Display suggestions
            if self.console:
                self.console.show_suggestion_details(filtered)
                if len(all_suggestions) > len(filtered):
                    self.console.console.print(
                        f"\n[dim]Showing {len(filtered)} of {len(all_suggestions)} total suggestions[/dim]\n"
                    )
                return ""
            else:
                return self._format_suggestions_text(filtered)

        except Exception as e:
            logger.error(f"Failed to analyze project: {e}", exc_info=True)
            return f"Error analyzing project: {e}"

    async def _suggest_for_task(self, task_description: str, suggestor) -> str:
        """
        Generate suggestions for a task.

        Args:
            task_description: Task description
            suggestor: ProactiveSuggestor instance

        Returns:
            Result message
        """
        try:
            # Analyze task complexity if available
            complexity_analysis = None
            if hasattr(self.agent, "complexity_detector"):
                complexity_analysis = self.agent.complexity_detector.analyze(
                    task_description
                )

            # Generate task-specific suggestions
            suggestions = suggestor.suggest_for_task(
                task_description, complexity_analysis
            )

            if not suggestions:
                return f"No specific suggestions for this task"

            # Display suggestions
            if self.console:
                self.console.show_suggestion_details(suggestions)
                return ""
            else:
                return self._format_suggestions_text(suggestions)

        except Exception as e:
            logger.error(f"Failed to generate task suggestions: {e}", exc_info=True)
            return f"Error generating suggestions: {e}"

    def _format_suggestions_text(self, suggestions: list) -> str:
        """
        Format suggestions as plain text.

        Args:
            suggestions: List of Suggestion objects

        Returns:
            Formatted text
        """
        if not suggestions:
            return "No suggestions"

        lines = ["Suggestions:", ""]

        for i, suggestion in enumerate(suggestions, 1):
            priority_value = (
                suggestion.priority.value
                if hasattr(suggestion.priority, "value")
                else suggestion.priority
            )

            lines.append(f"{i}. [{priority_value.upper()}] {suggestion.title}")
            lines.append(f"   {suggestion.description}")

            if hasattr(suggestion, "action_command") and suggestion.action_command:
                lines.append(f"   Action: {suggestion.action_command}")

            lines.append("")

        return "\n".join(lines)

    def _show_help(self) -> str:
        """
        Show help for suggest command.

        Returns:
            Help text
        """
        return """Suggest Command

Usage:
  /suggest file <path>          - Analyze specific file for improvements
  /suggest project              - Analyze entire project
  /suggest task <description>   - Get suggestions for a task
  /suggest <description>        - Same as 'task' (shorthand)
  /suggest help                 - Show this help message

Description:
  The suggestion system provides proactive recommendations based on:
  - Code patterns (testing, documentation, security, performance)
  - Task complexity analysis
  - Best practices and common pitfalls
  - Project structure

Examples:
  /suggest file src/main.py                    # Analyze main.py
  /suggest project                             # Analyze entire project
  /suggest task refactor authentication        # Get task-specific suggestions
  /suggest implement user login                # Shorthand for task suggestion

Note:
  Suggestions are non-intrusive and prioritized by importance.
  High-priority suggestions address security or correctness issues.
  Low-priority suggestions are style and performance improvements.
"""
