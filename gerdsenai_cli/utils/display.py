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
    # Get the project root (where gerdsenai-ascii-art.txt is located)
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    return project_root / "gerdsenai-ascii-art.txt"


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
        art_path = get_ascii_art_path()
        if not art_path.exists():
            console.print("[WARNING] ASCII art file not found", style="yellow")
            return

        with open(art_path, encoding="utf-8") as f:
            art_lines = f.readlines()

        # Remove trailing newlines but preserve the structure
        art_lines = [line.rstrip("\n") for line in art_lines]

        # Apply colors to the ASCII art
        colored_art = apply_color_to_ascii_art(art_lines)

        # Display with some padding
        console.print()
        console.print(Align.center(colored_art))
        console.print()

    except Exception as e:
        console.print(f"[ERROR] Error loading ASCII art: {e}", style="red")


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
    """Display the complete startup sequence."""
    # Clear screen for clean startup
    console.clear()

    # Show ASCII art
    show_ascii_art()

    # Show welcome message
    show_welcome_message()

    # Show getting started hint
    console.print(
        "[INFO] Type [bold cyan]/help[/bold cyan] to see available commands or start chatting with your AI assistant!",
        style="dim",
    )
    console.print()


def show_loading_spinner(message: str = "Loading...") -> None:
    """Show a loading message (placeholder for rich.spinner if needed)."""
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
