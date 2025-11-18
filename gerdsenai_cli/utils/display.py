"""
Display utilities for GerdsenAI CLI.

This module handles the presentation of ASCII art, welcome messages, and other
visual elements using Rich for colorful terminal output.
"""

from pathlib import Path

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .. import __version__

console = Console()


def get_ascii_art_path() -> Path:
    """Get the path to the ASCII art file."""
    # Get the project root and point to examples/ directory
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    return project_root / "examples" / "gerdsenai-ascii-art.txt"


def apply_color_to_ascii_art(art_lines: list[str]) -> Text:
    """
    Apply color scheme to ASCII art based on GerdsenAI logo colors.

    Args:
        art_lines: List of strings representing each line of ASCII art

    Returns:
        Rich Text object with applied colors
    """
    colored_text = Text()

    # Define color gradients
    rainbow_colors = ["red", "orange3", "yellow", "green", "blue", "magenta"]
    neural_colors = ["blue", "blue1", "purple", "purple4", "blue3", "cyan"]

    for line_num, line in enumerate(art_lines):
        colored_line = Text()

        for char_num, char in enumerate(line):
            if char.strip():  # Non-whitespace characters
                # Detect if we're in the logo area (rough estimation)
                if line_num < 35:  # Logo area
                    if char in ["G", "g"]:  # Rainbow for G characters
                        color_idx = char_num % len(rainbow_colors)
                        color = rainbow_colors[color_idx]
                    elif char in [
                        "$",
                        "X",
                        "x",
                        "+",
                        ";",
                        ":",
                        ".",
                    ]:  # Neural network fibers
                        color_idx = (char_num + line_num) % len(neural_colors)
                        color = neural_colors[color_idx]
                    else:  # Other logo characters
                        color = "bright_cyan"
                elif line_num >= 40:  # Text area "GerdsenAI CLI"
                    if char in ["G", "e", "r", "d", "s", "n", "A", "I"]:  # Main text
                        color = "bright_white"
                    elif char in ["C", "L", "I"]:  # CLI text
                        color = "gray70"
                    else:  # Other characters in text area
                        color = "gray50"
                else:  # Transition area
                    color = "dim_gray"

                colored_line.append(char, style=color)
            else:
                colored_line.append(char)  # Preserve whitespace

        colored_text.append(colored_line)
        colored_text.append("\n")

    return colored_text


def show_ascii_art() -> None:
    """Display the GerdsenAI ASCII art with colors."""
    try:
        # Check terminal width to decide if we should show ASCII art
        terminal_width = console.size.width
        if terminal_width < 80:
            # Terminal too narrow, show simplified logo
            show_simple_logo()
            return

        art_path = get_ascii_art_path()
        if not art_path.exists():
            show_simple_logo()
            return

        with open(art_path, encoding="utf-8") as f:
            art_lines = f.readlines()

        # Remove trailing newlines and limit width
        art_lines = [line.rstrip("\n") for line in art_lines]

        # Truncate lines that are too wide
        max_width = min(terminal_width - 4, 120)  # Leave some margin
        art_lines = [
            line[:max_width] if len(line) > max_width else line for line in art_lines
        ]

        # Apply simplified colors (avoid complex coloring that might cause issues)
        colored_art = apply_simple_color_to_ascii_art(art_lines)

        # Display with minimal padding
        console.print()
        console.print(colored_art)
        console.print()

    except Exception as e:
        console.print(f"[WARNING] Could not display ASCII art: {e}", style="yellow")
        show_simple_logo()


def show_simple_logo() -> None:
    """Display a simple text logo when ASCII art fails."""
    logo = Text()
    logo.append("█▀▀ █▀▀ █▀▀█ █▀▀▄ █▀▀ █▀▀ █▀▀▄ █▀▀█ ▀█", style="bright_cyan bold")
    logo.append("\n")
    logo.append("█▄█ █▀▀ █▄▄▀ █  █ ▀▀█ █▀▀ █  █ █▄▄█  █", style="cyan")
    logo.append("\n")
    logo.append("▀▀▀ ▀▀▀ ▀ ▀▀ ▀▀▀  ▀▀▀ ▀▀▀ ▀  ▀ ▀  ▀ ▀▀▀", style="blue")
    console.print()
    console.print(Align.center(logo))
    console.print()


def apply_simple_color_to_ascii_art(art_lines: list[str]) -> Text:
    """Apply simplified colors to ASCII art."""
    colored_text = Text()

    for line_num, line in enumerate(art_lines):
        if line_num < 20:  # Logo area
            colored_text.append(line, style="bright_cyan")
        elif line_num >= 40:  # Text area
            colored_text.append(line, style="bright_white")
        else:  # Transition area
            colored_text.append(line, style="cyan")
        colored_text.append("\n")

    return colored_text


def show_welcome_message() -> None:
    """Display welcome message and version info."""
    welcome_text = Text()
    welcome_text.append("Welcome to ", style="white")
    welcome_text.append("GerdsenAI CLI", style="bold bright_cyan")
    welcome_text.append(f" v{__version__}", style="dim")

    subtitle = Text(
        "A terminal-based agentic coding tool for local AI models",
        style="italic gray70",
    )

    # Create a panel with the welcome message
    welcome_panel = Panel(
        Align.center(Text.assemble(welcome_text, "\n", subtitle)),
        border_style="bright_cyan",
        padding=(1, 2),
        title="[AI Assistant Ready]",
        title_align="center",
    )

    console.print(welcome_panel)
    console.print()


def show_startup_sequence() -> None:
    """Display the complete startup sequence with ASCII art and Claude/Gemini-style layout (no emojis)."""
    console.clear()

    # Show ASCII art first
    show_ascii_art()

    # Build and show welcome panel (pre-init, so we don't show model/server yet)
    cwd = str(Path.cwd())
    welcome = build_welcome_panel(cwd=cwd)
    console.print()
    console.print(Align.center(welcome))
    console.print()

    # Tips and context warning
    show_tips()
    show_context_warning()

    # Prompt hint
    show_prompt_hint()
    console.print()


def show_loading_spinner(message: str = "Loading...") -> None:
    """Show a loading message. Simple text-based loading indicator."""
    console.print(f"[LOADING] {message}", style="yellow")


def show_error(message: str) -> None:
    """Display an error message."""
    console.print(f"[ERROR] {message}", style="bold red")


def show_success(message: str) -> None:
    """Display a success message."""
    console.print(f"[SUCCESS] {message}", style="bold green")


def show_info(message: str) -> None:
    """Display an info message."""
    console.print(f"[INFO] {message}", style="bold blue")


def show_warning(message: str) -> None:
    """Display a warning message."""
    console.print(f"[WARNING] {message}", style="bold yellow")


# ===== New Claude/Gemini-style helpers (no emojis) =====


def build_welcome_panel(cwd: str, model: str = "", server_url: str = "") -> Panel:
    """Create the top welcome panel with quick hints and cwd."""
    header = Text()
    header.append("Welcome to ", style="white")
    header.append("GerdsenAI CLI", style="bold bright_cyan")
    header.append("!", style="white")

    body = Text()
    body.append("\n\n")
    body.append("  /help for help, /status for your current setup\n", style="dim")
    body.append(f"\n  cwd: {cwd}", style="dim")
    if model:
        body.append(f"\n  model: {model}", style="dim")
    if server_url:
        body.append(f"\n  server: {server_url}", style="dim")

    content = Text.assemble(header, body)
    return Panel(content, border_style="bright_black")


def show_tips() -> None:
    """Print getting-started tips similar to reference CLIs."""
    console.print("Tips for getting started:", style="bold")
    console.print()
    console.print("  Run /init to create a GerdsenAI.md file with instructions")
    console.print("  Use AI to help with file analysis, editing, bash commands and git")
    console.print(
        "  Be as specific as you would with another engineer for the best results"
    )
    console.print("  Run /terminal-setup to set up terminal integration", style="green")
    console.print()


def show_context_warning() -> None:
    """Show a note when launched in home directory or outside a project."""
    try:
        cwd = Path.cwd()
        in_home = cwd == Path.home()
        in_git_repo = (cwd / ".git").exists()
        if in_home:
            text = Text()
            text.append("Note: ", style="bold")
            text.append(
                "You have launched gerdsenai in your home directory. "
                "For the best experience, launch it in a project directory instead.",
                style="yellow",
            )
            console.print(text)
            console.print()
        elif not in_git_repo:
            console.print(
                Text(
                    "Hint: No git repository detected. Consider initializing one for better project context.",
                    style="yellow",
                )
            )
            console.print()
    except Exception:
        # Non-fatal
        pass


def show_prompt_hint() -> None:
    """Show a simple prompt hint without panels to avoid cursor positioning issues."""
    console.print(
        "Try: 'write a test for <filepath>' or '/help' for commands", style="dim"
    )
    console.print("Type '/tools' to see all available tools", style="dim")


def show_footer_status(
    security_level: str = "strict",
    model: str = "",
    context_percent: int = 100,
) -> None:
    """Render a single-line footer status similar to Gemini footer (no emojis)."""
    footer = Text()
    footer.append("~ ", style="dim")
    footer.append(f" security: {security_level}", style="dim")
    if model:
        footer.append(f"    {model}", style="dim")
    else:
        footer.append("    no model", style="dim")
    footer.append(f" ({context_percent}% context left)", style="dim")
    console.print(footer)
