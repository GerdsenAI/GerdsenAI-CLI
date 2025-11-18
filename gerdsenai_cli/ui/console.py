"""
Enhanced console with rich TUI layout and syntax highlighting.

Provides a modern, bordered interface for the GerdsenAI CLI.
"""

import re
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.live import Live
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML

from .layout import GerdsenAILayout
from .status_display import IntelligenceActivity, StatusDisplayManager
from ..utils.status_messages import OperationType, get_status_message


class EnhancedConsole:
    """Enhanced console with rich TUI capabilities."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize enhanced console.
        
        Args:
            console: Rich console instance (creates new if None)
        """
        self.console = console or Console()
        self.layout = GerdsenAILayout(self.console)
        self.use_tui: bool = True
        self.status_display = StatusDisplayManager(self.console)
        self._live: Optional[Live] = None  # Track active Live display
        self._persistent_live: Optional[Live] = None  # Persistent Live for full session
        self._prompt_session: Optional[PromptSession] = None  # For input in TUI mode

    def set_tui_mode(self, enabled: bool) -> None:
        """Enable or disable TUI mode.
        
        Args:
            enabled: Whether to use TUI layout
        """
        self.use_tui = enabled
    
    def start_persistent_tui(self) -> None:
        """Start persistent Live TUI that stays on screen for the entire session."""
        if self.use_tui and not self._persistent_live:
            # Initialize layout with empty state
            self.layout.update_input("")
            self.layout.update_response("", is_code=False)
            
            # Start persistent Live display
            self._persistent_live = Live(
                self.layout.layout,
                console=self.console,
                refresh_per_second=10,
                transient=False,
            )
            self._persistent_live.start()
            
            # Create prompt session for input
            self._prompt_session = PromptSession()
    
    def stop_persistent_tui(self) -> None:
        """Stop persistent Live TUI."""
        if self._persistent_live:
            self._persistent_live.stop()
            self._persistent_live = None
    
    async def get_input_in_tui(self) -> str:
        """Get user input while maintaining the TUI display.
        
        Returns:
            User input string
        """
        if not self._prompt_session:
            self._prompt_session = PromptSession()
        
        # Temporarily stop Live to allow input
        if self._persistent_live:
            self._persistent_live.stop()
        
        try:
            # Get input with styled prompt
            user_input = await self._prompt_session.prompt_async(
                HTML('<style fg="#00FFFF" bold="true">GerdsenAI</style><prompt> > </prompt>'),
                multiline=False,
            )
            
            # Update layout with user input
            self.layout.update_input(user_input)
            self.layout.update_response("", is_code=False)
            
            # Restart Live display
            if self.use_tui:
                self._persistent_live = Live(
                    self.layout.layout,
                    console=self.console,
                    refresh_per_second=10,
                    transient=False,
                )
                self._persistent_live.start()
            
            return user_input.strip()
        
        except (KeyboardInterrupt, EOFError):
            # Restart Live before raising
            if self.use_tui and not self._persistent_live:
                self._persistent_live = Live(
                    self.layout.layout,
                    console=self.console,
                    refresh_per_second=10,
                    transient=False,
                )
                self._persistent_live.start()
            raise

    def _detect_code_blocks(self, text: str) -> list[dict]:
        """Detect code blocks in markdown-formatted text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of code block info dicts with 'language', 'code', 'start', 'end'
        """
        # Match ```language\ncode\n``` patterns
        pattern = r"```(\w+)?\n(.*?)```"
        matches = re.finditer(pattern, text, re.DOTALL)
        
        blocks = []
        for match in matches:
            language = match.group(1) or "text"
            code = match.group(2).strip()
            blocks.append({
                "language": language,
                "code": code,
                "start": match.start(),
                "end": match.end(),
            })
        
        return blocks

    def _render_response_with_syntax(self, response: str) -> None:
        """Render response with syntax highlighting for code blocks.
        
        Args:
            response: The response text potentially containing code blocks
        """
        code_blocks = self._detect_code_blocks(response)
        
        if not code_blocks:
            # No code blocks, render as plain text
            if self.use_tui:
                self.layout.update_response(response, is_code=False)
            else:
                self.console.print(Markdown(response))
            return
        
        # For TUI mode, we need to display just the first code block
        # (since update_response only shows one block at a time)
        # For now, prioritize showing code blocks
        if self.use_tui and code_blocks:
            # Show the complete response as text (simpler for now)
            # TODO: Enhance to show multiple code blocks in sequence
            self.layout.update_response(response, is_code=False)
        else:
            # Non-TUI mode: Print each section separately
            last_end = 0
            for block in code_blocks:
                # Print text before code block
                if block["start"] > last_end:
                    text_before = response[last_end:block["start"]].strip()
                    if text_before:
                        self.console.print(text_before)
                
                # Print code block with syntax highlighting
                syntax = Syntax(
                    block["code"],
                    block["language"],
                    theme="monokai",
                    line_numbers=True,
                )
                self.console.print(syntax)
                
                last_end = block["end"]
            
            # Print remaining text after last code block
            if last_end < len(response):
                text_after = response[last_end:].strip()
                if text_after:
                    self.console.print(text_after)

    def print_message(
        self,
        user_input: str,
        ai_response: str,
    ) -> None:
        """Print a message exchange with automatic code detection.
        
        Args:
            user_input: User's input
            ai_response: AI's response (may contain code blocks)
        """
        if self.use_tui:
            self.layout.update_input(user_input)
            self._render_response_with_syntax(ai_response)
            self.layout.render()
        else:
            # Fallback to simple printing
            self.console.print(f"[bold green]You:[/bold green] {user_input}")
            self.console.print(f"[bold blue]GerdsenAI:[/bold blue]")
            self._render_response_with_syntax(ai_response)

    def start_streaming(self, user_input: str) -> None:
        """Start streaming response display.
        
        Args:
            user_input: User's input to display
        """
        if self.use_tui:
            # If persistent Live is active, just update the layout
            # Otherwise use temporary Live for streaming
            if self._persistent_live:
                self.layout.update_input(user_input)
                self.layout.update_response("", is_code=False)
                self._persistent_live.update(self.layout.layout)
            else:
                # Initialize layout for streaming
                self.layout.update_input(user_input)
                self.layout.update_response("", is_code=False)
                
                # Start Live display for in-place updates
                self._live = Live(
                    self.layout.layout,
                    console=self.console,
                    refresh_per_second=10,  # 10 updates per second for smooth streaming
                    transient=False,  # Keep the final output visible
                )
                self._live.start()
        else:
            self.console.print(f"[bold green]You:[/bold green] {user_input}")
            self.console.print("[bold blue]GerdsenAI:[/bold blue]", end=" ")

    def stream_chunk(self, chunk: str, accumulated_response: str) -> None:
        """Stream a chunk of the response.
        
        Args:
            chunk: The new chunk to display
            accumulated_response: Full response so far (including this chunk)
        """
        if self.use_tui:
            # Update TUI with accumulated response
            self.layout.update_response(accumulated_response, is_code=False)
            
            # Update the active Live display (persistent or temporary)
            if self._persistent_live:
                self._persistent_live.update(self.layout.layout)
            elif self._live:
                self._live.update(self.layout.layout)
        else:
            # Print chunk without newline for streaming effect
            self.console.print(chunk, end="", style="white")

    def finish_streaming(self) -> None:
        """Finish streaming response display."""
        if self.use_tui:
            # If using persistent Live, keep it running
            # Only stop temporary Live
            if self._live and not self._persistent_live:
                self._live.stop()
                self._live = None
                self.console.print()  # Add spacing after response
        else:
            self.console.print()  # Final newline for non-TUI mode

    def update_status(
        self,
        model: Optional[str] = None,
        context_files: Optional[int] = None,
        token_count: Optional[int] = None,
        current_task: Optional[str] = None,
        operation: Optional[str] = None,
    ) -> None:
        """Update status bar.
        
        Args:
            model: Current model name
            context_files: Number of context files
            token_count: Token count
            current_task: Current task description
            operation: Operation type (e.g., 'thinking', 'reading', 'analyzing')
        """
        # If operation is provided, generate a sophisticated status message
        if operation and operation.upper() in OperationType.__members__:
            op_type = OperationType[operation.upper()]
            current_task = get_status_message(op_type)
        
        if self.use_tui:
            self.layout.update_status(
                model=model,
                context_files=context_files,
                token_count=token_count,
                current_task=current_task,
            )
    
    def set_operation(self, operation: str) -> None:
        """Set current operation with sophisticated status message.
        
        Args:
            operation: Operation type (thinking, reading, analyzing, writing, planning,
                      searching, processing, streaming, contextualizing, synthesizing, evaluating)
        """
        self.update_status(operation=operation)

    def get_input(self, prompt: str = ">>> ") -> str:
        """Get user input.
        
        Args:
            prompt: Prompt text
            
        Returns:
            User input string
        """
        return Prompt.ask(prompt, console=self.console)

    def confirm(
        self,
        message: str,
        default: bool = False,
    ) -> bool:
        """Get confirmation from user.
        
        Args:
            message: Confirmation message
            default: Default value if user just presses Enter
            
        Returns:
            True if confirmed, False otherwise
        """
        return Confirm.ask(message, default=default, console=self.console)

    def clear(self) -> None:
        """Clear the console."""
        self.layout.clear()

    def print_error(self, message: str) -> None:
        """Print an error message.
        
        Args:
            message: Error message
        """
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def print_success(self, message: str) -> None:
        """Print a success message.
        
        Args:
            message: Success message
        """
        self.console.print(f"[bold green]Success:[/bold green] {message}")

    def print_info(self, message: str) -> None:
        """Print an info message.
        
        Args:
            message: Info message
        """
        self.console.print(f"[bold blue]Info:[/bold blue] {message}")

    def print_warning(self, message: str) -> None:
        """Print a warning message.
        
        Args:
            message: Warning message
        """
        self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")

    def set_intelligence_activity(
        self,
        activity: IntelligenceActivity,
        message: str,
        progress: float | None = None,
        details: dict | None = None,
        step_info: str | None = None,
    ) -> None:
        """Set current intelligence activity for display.

        Args:
            activity: Type of intelligence activity
            message: Display message
            progress: Optional progress (0.0 to 1.0)
            details: Optional activity details
            step_info: Optional step information (e.g., "Step 2/5")
        """
        self.status_display.set_activity(activity, message, progress, details, step_info)

        # Update layout with new status
        if self.use_tui:
            status_line = self.status_display.get_status_line()
            self.layout.update_status(current_task=status_line)

    def update_intelligence_progress(
        self, progress: float, step_info: str | None = None
    ) -> None:
        """Update progress of current intelligence activity.

        Args:
            progress: New progress value (0.0 to 1.0)
            step_info: Optional updated step information
        """
        self.status_display.update_progress(progress, step_info)

        if self.use_tui:
            status_line = self.status_display.get_status_line()
            self.layout.update_status(current_task=status_line)

    def clear_intelligence_activity(self) -> None:
        """Clear current intelligence activity."""
        self.status_display.clear_activity()

        if self.use_tui:
            self.layout.update_status(current_task="💤 Ready")

    def show_intelligence_details(self) -> None:
        """Show detailed intelligence activity history."""
        table = self.status_display.get_detailed_status()
        self.console.print("\n")
        self.console.print(table)
        self.console.print("\n")

    def get_intelligence_summary(self) -> dict:
        """Get summary of intelligence activity statistics.

        Returns:
            Dictionary with activity counts and timing info
        """
        return self.status_display.get_activity_summary()

    def show_clarifying_question(self, question) -> int | None:
        """
        Display a clarifying question with interpretations and get user choice.

        Args:
            question: ClarifyingQuestion object with interpretations

        Returns:
            Selected interpretation ID, or None if cancelled
        """
        from rich.panel import Panel
        from rich.table import Table

        # Show the question
        self.console.print()
        self.console.print(
            Panel(
                f"[yellow]{question.question}[/yellow]",
                title="Clarification Needed",
                border_style="yellow",
            )
        )

        # Create table of interpretations
        table = Table(
            title="Possible Interpretations",
            show_header=True,
            header_style="bold cyan",
            border_style="dim",
        )

        table.add_column("#", style="cyan", width=3)
        table.add_column("Interpretation", style="white", ratio=3)
        table.add_column("Confidence", style="dim", width=10)
        table.add_column("Details", style="dim", ratio=2)

        for interp in question.interpretations:
            confidence_bar = "█" * int(interp.confidence * 10)
            confidence_str = f"{confidence_bar} {interp.confidence:.0%}"

            details = interp.reasoning
            if interp.risks:
                details += f"\n[red]Risks: {', '.join(interp.risks)}[/red]"

            table.add_row(
                str(interp.id),
                f"[bold]{interp.title}[/bold]\n{interp.description}",
                confidence_str,
                details,
            )

        self.console.print(table)
        self.console.print()

        # Get user choice
        while True:
            choice_str = Prompt.ask(
                "Select an interpretation",
                choices=[str(i.id) for i in question.interpretations] + ["cancel"],
                default="1",
            )

            if choice_str.lower() == "cancel":
                return None

            try:
                choice_id = int(choice_str)
                # Validate choice
                if any(i.id == choice_id for i in question.interpretations):
                    return choice_id
            except ValueError:
                pass

            self.console.print("[red]Invalid choice. Please try again.[/red]")

    def show_clarification_stats(self, stats: dict) -> None:
        """
        Display clarification statistics.

        Args:
            stats: Statistics dictionary from ClarificationEngine
        """
        from rich.panel import Panel
        from rich.table import Table

        table = Table(title="Clarification Statistics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Total Clarifications", str(stats.get("total_clarifications", 0)))
        table.add_row(
            "Helpful Rate", f"{stats.get('helpful_rate', 0.0) * 100:.1f}%"
        )
        table.add_row("Most Common Type", str(stats.get("most_common_type", "N/A")))

        # Type breakdown
        if "type_breakdown" in stats:
            table.add_row("", "")  # Spacer
            table.add_row("[bold]Type Breakdown[/bold]", "")
            for type_name, count in stats["type_breakdown"].items():
                table.add_row(f"  {type_name}", str(count))

        self.console.print()
        self.console.print(Panel(table, border_style="cyan"))
        self.console.print()

    def show_complexity_analysis(self, analysis) -> None:
        """
        Display complexity analysis result.

        Args:
            analysis: ComplexityAnalysis object
        """
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        # Main analysis panel
        complexity_color = {
            "trivial": "green",
            "simple": "green",
            "moderate": "yellow",
            "complex": "orange",
            "very_complex": "red",
        }.get(analysis.complexity_level.value, "white")

        risk_color = {
            "minimal": "green",
            "low": "green",
            "medium": "yellow",
            "high": "red",
            "critical": "bold red",
        }.get(analysis.risk_level.value, "white")

        # Header with complexity and risk
        header = Text()
        header.append("Complexity: ", style="bold")
        header.append(
            f"{analysis.complexity_level.value.upper().replace('_', ' ')}",
            style=f"bold {complexity_color}"
        )
        header.append(" | Risk: ", style="bold")
        header.append(
            f"{analysis.risk_level.value.upper()}",
            style=f"bold {risk_color}"
        )

        self.console.print()
        self.console.print(Panel(header, title="Task Complexity Analysis", border_style="cyan"))

        # Reasoning
        self.console.print()
        self.console.print("[bold]Analysis:[/bold]", analysis.reasoning)

        # Resource Estimate
        self.console.print()
        est_table = Table(title="Resource Estimate", show_header=True, border_style="dim")
        est_table.add_column("Resource", style="cyan")
        est_table.add_column("Estimate", style="white")

        est = analysis.resource_estimate
        hours = est.estimated_time_minutes // 60
        mins = est.estimated_time_minutes % 60
        time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"

        est_table.add_row("Estimated Time", time_str)
        est_table.add_row("Steps", str(est.estimated_steps))
        est_table.add_row("Files Affected", str(est.file_count))
        est_table.add_row("Lines of Code", f"~{est.lines_of_code}")
        est_table.add_row(
            "Tests Needed",
            "✓ Yes" if est.test_coverage_needed else "- No"
        )
        est_table.add_row(
            "Docs Needed",
            "✓ Yes" if est.documentation_needed else "- No"
        )

        self.console.print(est_table)

        # Impact Assessment
        self.console.print()
        impact_table = Table(title="Impact Assessment", show_header=True, border_style="dim")
        impact_table.add_column("Aspect", style="cyan")
        impact_table.add_column("Details", style="white")

        impact = analysis.impact_assessment
        impact_table.add_row(
            "Scope",
            impact.impact_scope.value.replace("_", " ").title()
        )
        impact_table.add_row(
            "Components",
            ", ".join(impact.affected_components)
        )

        if impact.potential_side_effects:
            impact_table.add_row(
                "Side Effects",
                "\n".join(f"• {effect}" for effect in impact.potential_side_effects)
            )

        impact_table.add_row(
            "Breaking Changes",
            "[red]Likely[/red]" if impact.breaking_changes_likely else "[green]Unlikely[/green]"
        )

        impact_table.add_row(
            "Migration Needed",
            "[yellow]Yes[/yellow]" if impact.requires_migration else "[green]No[/green]"
        )

        self.console.print(impact_table)

        # Warnings
        if analysis.warnings:
            self.console.print()
            warning_panel = Panel(
                "\n".join(analysis.warnings),
                title="⚠️  Warnings",
                border_style="yellow",
                style="yellow"
            )
            self.console.print(warning_panel)

        # Recommendations
        if analysis.recommendations:
            self.console.print()
            self.console.print("[bold cyan]Recommendations:[/bold cyan]")
            for i, rec in enumerate(analysis.recommendations, 1):
                self.console.print(f"  {i}. {rec}")

        # Planning/Confirmation suggestions
        self.console.print()
        if analysis.requires_planning:
            self.console.print(
                "[bold yellow]💡 Suggestion:[/bold yellow] Use multi-step planning for this task (/plan)"
            )

        if analysis.requires_confirmation:
            self.console.print(
                "[bold red]🔒 Required:[/bold red] User confirmation needed before execution"
            )

        self.console.print()

    def show_confirmation_dialog(self, preview) -> str | None:
        """
        Display confirmation dialog for high-risk operation.

        Args:
            preview: OperationPreview object

        Returns:
            User response: "yes", "no", "preview", or None if error
        """
        from rich.panel import Panel
        from rich.table import Table

        # Color code by risk level
        risk_colors = {
            "minimal": "green",
            "low": "green",
            "medium": "yellow",
            "high": "red",
            "critical": "bold red",
        }

        risk_color = risk_colors.get(preview.risk_level, "yellow")

        # Header
        self.console.print()
        self.console.print(
            Panel(
                f"[bold {risk_color}]⚠ CONFIRMATION REQUIRED[/bold {risk_color}]\n\n"
                f"Operation: {preview.description}\n"
                f"Risk Level: [{risk_color}]{preview.risk_level.upper()}[/{risk_color}]\n"
                f"Estimated Time: {preview.estimated_time} minutes\n"
                f"Reversible: {'Yes' if preview.reversible else 'No'}",
                title="Operation Preview",
                border_style=risk_color,
            )
        )

        # Affected files summary
        if preview.affected_files:
            files_table = Table(title="Affected Files", show_header=True)
            files_table.add_column("File", style="cyan")
            files_table.add_column("Operation", style="magenta")
            files_table.add_column("Impact", justify="center")
            files_table.add_column("Changes")

            for file_change in preview.affected_files[:20]:  # Limit to 20 files
                impact_color = {
                    "low": "green",
                    "medium": "yellow",
                    "high": "red",
                }.get(file_change.estimated_impact, "white")

                changes = ""
                if file_change.lines_added > 0:
                    changes += f"+{file_change.lines_added} "
                if file_change.lines_removed > 0:
                    changes += f"-{file_change.lines_removed}"

                files_table.add_row(
                    file_change.path,
                    file_change.operation,
                    f"[{impact_color}]{file_change.estimated_impact}[/{impact_color}]",
                    changes or "N/A",
                )

            if len(preview.affected_files) > 20:
                files_table.add_row(
                    f"... and {len(preview.affected_files) - 20} more",
                    "",
                    "",
                    "",
                )

            self.console.print(files_table)

        # Warnings
        if preview.warnings:
            self.console.print()
            warning_panel = Panel(
                "\n".join(f"⚠ {warning}" for warning in preview.warnings),
                title="Warnings",
                border_style="red",
            )
            self.console.print(warning_panel)

        # Recommendations
        if preview.recommendations:
            self.console.print()
            self.console.print("[bold]Recommendations:[/bold]")
            for i, rec in enumerate(preview.recommendations[:5], 1):
                self.console.print(f"  {i}. {rec}")

        # Prompt for confirmation
        self.console.print()
        self.console.print(
            "[bold]Do you want to proceed with this operation?[/bold]"
        )
        self.console.print(
            "  [green]yes[/green] - Proceed with operation"
        )
        self.console.print(
            "  [red]no[/red] - Cancel operation"
        )
        self.console.print(
            "  [cyan]preview[/cyan] - Show detailed diff preview"
        )

        # Get user input
        response = input("\nYour choice (yes/no/preview): ").strip().lower()

        if response in ["y", "yes"]:
            return "yes"
        elif response in ["n", "no"]:
            return "no"
        elif response in ["p", "preview"]:
            return "preview"
        else:
            self.console.print("[yellow]Invalid response. Operation cancelled.[/yellow]")
            return "no"

    def show_file_diff(self, file_change) -> None:
        """
        Display file diff in unified diff format.

        Args:
            file_change: FileChange object
        """
        from rich.panel import Panel
        from rich.syntax import Syntax

        self.console.print()
        self.console.print(
            Panel(
                f"[bold]File:[/bold] {file_change.path}\n"
                f"[bold]Operation:[/bold] {file_change.operation}\n"
                f"[bold]Impact:[/bold] {file_change.estimated_impact}\n"
                f"[bold]Changes:[/bold] +{file_change.lines_added} -{file_change.lines_removed}",
                title=f"Diff: {file_change.path}",
                border_style="cyan",
            )
        )

        if file_change.operation == "delete":
            if file_change.old_content:
                # Show content being deleted
                syntax = Syntax(
                    file_change.old_content[:1000],  # Limit to first 1000 chars
                    "python",
                    theme="monokai",
                    line_numbers=True,
                )
                self.console.print("[red]Content to be deleted:[/red]")
                self.console.print(syntax)

        elif file_change.operation == "create":
            if file_change.new_content:
                # Show new content
                syntax = Syntax(
                    file_change.new_content[:1000],
                    "python",
                    theme="monokai",
                    line_numbers=True,
                )
                self.console.print("[green]Content to be created:[/green]")
                self.console.print(syntax)

        elif file_change.operation == "modify":
            if file_change.old_content and file_change.new_content:
                # Generate simple diff
                old_lines = file_change.old_content.splitlines()
                new_lines = file_change.new_content.splitlines()

                diff_lines = []
                max_lines = max(len(old_lines), len(new_lines))

                for i in range(min(max_lines, 50)):  # Limit to 50 lines
                    old_line = old_lines[i] if i < len(old_lines) else ""
                    new_line = new_lines[i] if i < len(new_lines) else ""

                    if old_line != new_line:
                        if old_line:
                            diff_lines.append(f"- {old_line}")
                        if new_line:
                            diff_lines.append(f"+ {new_line}")

                if diff_lines:
                    syntax = Syntax(
                        "\n".join(diff_lines),
                        "diff",
                        theme="monokai",
                        line_numbers=False,
                    )
                    self.console.print(syntax)

        self.console.print()

    def show_undo_snapshots(self, snapshots: list) -> None:
        """
        Display list of available undo snapshots.

        Args:
            snapshots: List of UndoSnapshot objects
        """
        from rich.table import Table

        if not snapshots:
            self.console.print("[yellow]No undo snapshots available[/yellow]")
            return

        table = Table(title="Available Undo Snapshots", show_header=True)
        table.add_column("#", style="cyan", width=3)
        table.add_column("Snapshot ID", style="magenta")
        table.add_column("Operation", style="white")
        table.add_column("Description", style="white", width=40)
        table.add_column("Files", justify="right")
        table.add_column("Timestamp", style="dim")
        table.add_column("Expires", style="yellow")

        for i, snapshot in enumerate(snapshots, 1):
            # Calculate time until expiration
            from datetime import datetime

            expires_at = datetime.fromisoformat(snapshot.expires_at)
            now = datetime.now()
            time_left = expires_at - now

            hours_left = int(time_left.total_seconds() / 3600)
            expires_str = f"{hours_left}h" if hours_left > 0 else "expired"

            # Truncate description if too long
            description = snapshot.description
            if len(description) > 40:
                description = description[:37] + "..."

            table.add_row(
                str(i),
                snapshot.snapshot_id,
                snapshot.operation_type.value,
                description,
                str(len(snapshot.affected_files)),
                snapshot.timestamp.split("T")[0],  # Date only
                expires_str,
            )

        self.console.print(table)
        self.console.print(
            f"\nTotal snapshots: {len(snapshots)} | Use /undo to restore the last operation"
        )

    def show_undo_result(self, success: bool, message: str, files_restored: int = 0) -> None:
        """
        Display result of undo operation.

        Args:
            success: Whether undo was successful
            message: Result message
            files_restored: Number of files restored
        """
        from rich.panel import Panel

        if success:
            panel = Panel(
                f"[bold green]✓ Undo Successful[/bold green]\n\n"
                f"{message}\n\n"
                f"Files restored: {files_restored}",
                border_style="green",
            )
        else:
            panel = Panel(
                f"[bold red]✗ Undo Failed[/bold red]\n\n{message}",
                border_style="red",
            )

        self.console.print()
        self.console.print(panel)
        self.console.print()

    def show_suggestions(self, suggestions: list, max_display: int = 3) -> None:
        """
        Display proactive suggestions in a non-intrusive way.

        Args:
            suggestions: List of Suggestion objects
            max_display: Maximum number of suggestions to display
        """
        from rich.panel import Panel
        from rich.table import Table

        if not suggestions:
            return

        # Limit display
        display_suggestions = suggestions[:max_display]

        # Priority colors
        priority_colors = {
            "critical": "bold red",
            "high": "yellow",
            "medium": "cyan",
            "low": "dim",
        }

        # Build suggestions table
        table = Table(title="💡 Proactive Suggestions", show_header=True, box=None)
        table.add_column("#", style="dim", width=3)
        table.add_column("Priority", width=10)
        table.add_column("Suggestion", style="bold")
        table.add_column("Benefit")

        for i, suggestion in enumerate(display_suggestions, 1):
            # Get priority value (handle both enum and string)
            priority_value = (
                suggestion.priority.value
                if hasattr(suggestion.priority, "value")
                else suggestion.priority
            )
            priority_color = priority_colors.get(priority_value, "white")

            # Get main benefit
            benefits = suggestion.benefits if hasattr(suggestion, "benefits") else []
            main_benefit = benefits[0] if benefits else "Improves code quality"

            table.add_row(
                str(i),
                f"[{priority_color}]{priority_value.upper()}[/{priority_color}]",
                suggestion.title,
                main_benefit,
            )

        # Show with minimal visual impact
        self.console.print()
        self.console.print(table)

        # Show additional info if user wants
        if len(suggestions) > max_display:
            self.console.print(
                f"\n[dim]... and {len(suggestions) - max_display} more suggestion(s)[/dim]"
            )

        self.console.print(
            "\n[dim]Use /suggest for detailed suggestions or dismiss to continue[/dim]"
        )
        self.console.print()

    def show_suggestion_details(self, suggestions: list) -> None:
        """
        Display detailed information about suggestions.

        Args:
            suggestions: List of Suggestion objects
        """
        from rich.panel import Panel
        from rich.table import Table

        if not suggestions:
            self.console.print("[yellow]No suggestions available[/yellow]")
            return

        # Priority colors
        priority_colors = {
            "critical": "bold red",
            "high": "yellow",
            "medium": "cyan",
            "low": "white",
        }

        for i, suggestion in enumerate(suggestions, 1):
            # Get priority value
            priority_value = (
                suggestion.priority.value
                if hasattr(suggestion, "value")
                else suggestion.priority
            )
            priority_color = priority_colors.get(priority_value, "white")

            # Get type value
            type_value = (
                suggestion.suggestion_type.value
                if hasattr(suggestion.suggestion_type, "value")
                else suggestion.category
            )

            # Build content
            content = f"[bold]Type:[/bold] {type_value}\n"
            content += f"[bold]Priority:[/bold] [{priority_color}]{priority_value.upper()}[/{priority_color}]\n\n"
            content += f"{suggestion.description}\n"

            if hasattr(suggestion, "reasoning") and suggestion.reasoning:
                content += f"\n[bold]Reasoning:[/bold] {suggestion.reasoning}"

            if hasattr(suggestion, "affected_files") and suggestion.affected_files:
                content += f"\n[bold]Affected Files:[/bold] {', '.join(suggestion.affected_files[:3])}"
                if len(suggestion.affected_files) > 3:
                    content += f" (+{len(suggestion.affected_files) - 3} more)"

            if hasattr(suggestion, "code_example") and suggestion.code_example:
                content += f"\n\n[bold]Example:[/bold]\n[dim]{suggestion.code_example}[/dim]"

            if hasattr(suggestion, "action_command") and suggestion.action_command:
                content += f"\n\n[bold green]Action:[/bold green] {suggestion.action_command}"

            if hasattr(suggestion, "estimated_time"):
                content += f"\n[bold]Estimated Time:[/bold] ~{suggestion.estimated_time} minutes"

            if hasattr(suggestion, "benefits") and suggestion.benefits:
                content += "\n\n[bold]Benefits:[/bold]"
                for benefit in suggestion.benefits:
                    content += f"\n  • {benefit}"

            # Display in panel
            panel = Panel(
                content,
                title=f"[{priority_color}]Suggestion {i}: {suggestion.title}[/{priority_color}]",
                border_style=priority_color,
            )

            self.console.print()
            self.console.print(panel)

        self.console.print()
        self.console.print(f"[dim]Total: {len(suggestions)} suggestion(s)[/dim]")
        self.console.print()
