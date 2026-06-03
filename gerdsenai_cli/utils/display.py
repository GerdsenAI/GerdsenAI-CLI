"""
Display utilities for GerdsenAI CLI.

This module handles the presentation of ASCII art, welcome messages, and other
visual elements using Rich for colorful terminal output.
"""

from importlib import resources
from pathlib import Path

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

ASCII_ART_FILENAME = "gerdsenai-ascii-art.txt"


def set_quiet_mode(enabled: bool) -> None:
    """Route diagnostic output (show_info/warning/success/error) to stderr.

    Used by headless mode so that stdout carries ONLY the agent's answer and
    stays clean for piping (``gerdsenai -p ... | jq``). All show_* helpers below
    resolve ``console`` from this module's globals at call time, so reassigning
    it here transparently redirects every diagnostic without touching call sites.
    """
    global console
    console = Console(stderr=enabled)


def get_ascii_art_path() -> Path:
    """Return the filesystem path to the packaged ASCII art asset.

    The asset ships inside the ``gerdsenai_cli`` package (``assets/``), so this
    works both from a source checkout and from an installed wheel.
    """
    return Path(str(resources.files("gerdsenai_cli") / "assets" / ASCII_ART_FILENAME))


def get_logo_text() -> str:
    """Load the raw ASCII logo text from the packaged asset.

    Returns an empty string if the asset cannot be read.
    """
    try:
        return (
            resources.files("gerdsenai_cli")
            .joinpath("assets", ASCII_ART_FILENAME)
            .read_text(encoding="utf-8")
        )
    except (FileNotFoundError, OSError, ModuleNotFoundError):
        return ""


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


def show_startup_sequence() -> None:
    """Display the pre-TUI startup banner (welcome panel, tips, prompt hints).

    The canonical ASCII logo is rendered by the TUI itself (see
    ``PromptToolkitTUI._load_ascii_art``); this banner intentionally does not
    repeat it.
    """
    console.clear()

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
