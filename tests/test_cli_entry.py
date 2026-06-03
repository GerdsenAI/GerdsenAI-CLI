"""The console entry point (app) must actually parse args.

Guards the cli:main -> cli:app packaging fix: the old console_scripts target
called the @app.command() function directly, so its typer.OptionInfo defaults
were truthy and EVERY invocation just printed the version and exited, ignoring
all flags. These tests exercise the real `app` callable the script now points at.
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

import gerdsenai_cli.utils.display as display
from gerdsenai_cli.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _restore_console():
    """run_headless flips display to a stderr console; restore it after each test."""
    original = display.console
    yield
    display.console = original


def test_app_reports_version():
    """--version prints the version and exits 0"""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "GerdsenAI CLI v" in result.output


def test_app_exposes_headless_options():
    """--help lists the headless flags, proving the app parses args (not just version)"""
    result = runner.invoke(app, ["--help"], env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert "--prompt" in result.output
    assert "--stdin" in result.output


def test_app_headless_no_config_exits_one(monkeypatch, tmp_path):
    """-p with no config fails fast (exit 1) through the real app entry — no hang"""
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(app, ["-p", "hi"])
    assert result.exit_code == 1
