#!/usr/bin/env python3
"""
GerdsenAI CLI - Main entry point.

This module serves as the main entry point for the CLI application.
"""

import asyncio
import sys

import typer
from rich.console import Console

from .main import GerdsenAICLI
from .utils.display import show_error

console = Console()
app = typer.Typer(
    name="gerdsenai",
    help="GerdsenAI CLI - A terminal-based agentic coding tool for local AI models",
    add_completion=False,
    no_args_is_help=False,
)


@app.command()
def main(
    config_path: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug mode",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit",
    ),
    prompt: str | None = typer.Option(
        None,
        "--prompt",
        "-p",
        help="Run a single prompt non-interactively, print the answer, and exit",
    ),
    stdin_input: bool = typer.Option(
        False,
        "--stdin",
        help="Read the prompt from stdin (use with a pipe)",
    ),
    mode: str = typer.Option(
        "execute",
        "--mode",
        help="Execution mode for headless -p: chat, architect, execute, or llvl",
    ),
) -> None:
    """
    Start the GerdsenAI CLI interactive session.
    """
    if version:
        from . import __version__

        console.print(f"GerdsenAI CLI v{__version__}")
        return

    # Headless one-shot mode: run a single turn and exit (no TUI).
    if prompt is not None or stdin_input:
        text = prompt if prompt is not None else sys.stdin.read().strip()
        if not text:
            show_error("No prompt provided (use -p TEXT or pipe text with --stdin).")
            sys.exit(2)
        cli = GerdsenAICLI(config_path=config_path, debug=debug, interactive=False)
        sys.exit(asyncio.run(cli.run_headless(text, mode=mode)))

    try:
        # Initialize and run the CLI (startup sequence shown in run_async)
        cli = GerdsenAICLI(config_path=config_path, debug=debug)
        cli.run()

    except KeyboardInterrupt:
        console.print("\nGoodbye!", style="bright_cyan")
        sys.exit(0)
    except Exception as e:
        if debug:
            console.print_exception()
        else:
            show_error(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    app()
