"""Regression test for the mode-sync fix: the TUI's execution-mode selection
must reach the Settings instance the agent reads on every turn."""
from __future__ import annotations

from types import SimpleNamespace

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.core.modes import ExecutionMode
from gerdsenai_cli.main import _persist_agent_mode


def test_persist_agent_mode_writes_every_mode_to_settings():
    """_persist_agent_mode mirrors the TUI mode into agent.settings['agent_mode']"""
    agent = SimpleNamespace(settings=Settings())
    cases = [
        (ExecutionMode.CHAT, "chat"),
        (ExecutionMode.ARCHITECT, "architect"),
        (ExecutionMode.EXECUTE, "execute"),
        (ExecutionMode.LLVL, "llvl"),
    ]
    for mode, expected in cases:
        _persist_agent_mode(agent, mode)
        assert agent.settings.get_preference("agent_mode") == expected
