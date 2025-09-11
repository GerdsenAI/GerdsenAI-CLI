#!/usr/bin/env python3
"""
GerdsenAI CLI - Main entry point.

This module serves as the main entry point for the CLI application.
"""

import sys
from typing import Optional

import typer
from rich.console import Console

from .main import GerdsenAICLI
from .utils.display import show_error, show_startup_sequence

console = Console()
app = typer.Typer(
    name="gerdsenai",
    help="GerdsenAI CLI - A terminal-based agentic coding tool for local AI models",
    add_completion=False,
    no_args_is_help=False,
)


@app.command()
def main(
    config_path: Optional[str] = typer.Option(
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
) -> None:
    """
    Start the GerdsenAI CLI interactive session.
    """
    if version:
        from . import __version__
        console.print(f"GerdsenAI CLI v{__version__}")
        return

    try:
        # Show startup sequence
        show_startup_sequence()
        
        # Initialize and run the CLI
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
