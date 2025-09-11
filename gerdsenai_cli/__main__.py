"""
Entry point for running GerdsenAI CLI as a module.

This allows the package to be executed with: python -m gerdsenai_cli
"""

from .cli import app

if __name__ == "__main__":
    app()
