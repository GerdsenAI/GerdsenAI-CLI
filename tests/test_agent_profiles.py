"""Tests for agent profiles (personas) and the /persona command."""

from __future__ import annotations

from pathlib import Path

import pytest

from gerdsenai_cli.commands.persona import PersonaCommand
from gerdsenai_cli.config.manager import ConfigManager
from gerdsenai_cli.core.agent_profiles import AgentProfile, AgentProfileManager


@pytest.fixture
def manager(tmp_path: Path) -> AgentProfileManager:
    config = ConfigManager(str(tmp_path / "config.json"))
    return AgentProfileManager(config)


# --------------------------------------------------------------------------- #
# AgentProfile / manager
# --------------------------------------------------------------------------- #


def test_profile_roundtrip() -> None:
    p = AgentProfile(name="rev", model="m", provider="ollama", system_prompt="be terse")
    restored = AgentProfile.from_dict("rev", p.to_dict())
    assert restored == p


def test_add_get_list_remove(manager: AgentProfileManager) -> None:
    assert manager.list() == []
    assert manager.add(AgentProfile(name="rev", model="qwen", provider="ollama"))
    assert manager.add(
        AgentProfile(name="arch", model="claude-opus-4-8", provider="anthropic")
    )

    names = {p.name for p in manager.list()}
    assert names == {"rev", "arch"}
    assert manager.get("rev").model == "qwen"
    assert manager.get("missing") is None

    assert manager.remove("rev")
    assert manager.get("rev") is None
    assert not manager.remove("rev")  # already gone


def test_set_active_switches_model(manager: AgentProfileManager) -> None:
    manager.add(
        AgentProfile(name="arch", model="claude-opus-4-8", provider="anthropic")
    )
    profile = manager.set_active("arch")
    assert profile is not None
    assert manager.get_active().name == "arch"
    # Activating a persona switches the current model.
    assert manager.config.get_settings().current_model == "claude-opus-4-8"

    assert manager.set_active("nope") is None  # unknown profile


def test_remove_active_clears_pointer(manager: AgentProfileManager) -> None:
    manager.add(AgentProfile(name="rev", model="m"))
    manager.set_active("rev")
    assert manager.get_active() is not None
    manager.remove("rev")
    assert manager.config.get_settings().active_agent_profile == ""


# --------------------------------------------------------------------------- #
# /persona command
# --------------------------------------------------------------------------- #


def test_command_parse_arguments() -> None:
    cmd = PersonaCommand()
    assert cmd.parse_arguments("") == {"action": "list", "rest": ""}
    assert cmd.parse_arguments("add rev qwen ollama") == {
        "action": "add",
        "rest": "rev qwen ollama",
    }
    assert cmd.parse_arguments("system rev You are terse") == {
        "action": "system",
        "rest": "rev You are terse",
    }
    assert cmd.parse_arguments("bogus") == {"action": "help", "rest": ""}


@pytest.mark.asyncio
async def test_command_add_use_flow(tmp_path: Path) -> None:
    config = ConfigManager(str(tmp_path / "config.json"))
    ctx = {"config_manager": config}
    cmd = PersonaCommand()

    add = await cmd.execute(
        cmd.parse_arguments("add arch claude-opus-4-8 anthropic"), ctx
    )
    assert add.success and "Created" in (add.message or "")

    sys_r = await cmd.execute(
        cmd.parse_arguments("system arch You are a software architect"), ctx
    )
    assert sys_r.success

    # Use it; a fake agent in context should receive the persona + model.
    class FakeSettings:
        current_model = ""

    class FakeAgent:
        persona_context = ""
        settings = FakeSettings()

    agent = FakeAgent()
    use = await cmd.execute(cmd.parse_arguments("use arch"), {**ctx, "agent": agent})
    assert use.success
    assert agent.persona_context == "You are a software architect"
    assert agent.settings.current_model == "claude-opus-4-8"

    listed = await cmd.execute(cmd.parse_arguments("list"), ctx)
    assert listed.success and "1 persona" in (listed.message or "")


@pytest.mark.asyncio
async def test_command_empty_and_missing(tmp_path: Path) -> None:
    config = ConfigManager(str(tmp_path / "config.json"))
    ctx = {"config_manager": config}
    cmd = PersonaCommand()

    listed = await cmd.execute(cmd.parse_arguments("list"), ctx)
    assert listed.success and "No personas" in (listed.message or "")

    missing = await cmd.execute(cmd.parse_arguments("use ghost"), ctx)
    assert not missing.success

    bad_add = await cmd.execute(cmd.parse_arguments("add onlyname"), ctx)
    assert not bad_add.success  # needs a model
