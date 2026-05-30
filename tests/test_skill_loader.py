"""Tests for imported skill/agent discovery and the /skills command."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from gerdsenai_cli.commands.skills import SkillCommand, SkillsCommand
from gerdsenai_cli.core.skill_loader import (
    Skill,
    _parse_frontmatter,
    build_skills_context,
    discover_skills,
)


def _skill(name: str, body: str = "body", kind: str = "skill") -> Skill:
    return Skill(name=name, description="d", body=body, source=Path("x"), kind=kind)


# --------------------------------------------------------------------------- #
# parsing / slug
# --------------------------------------------------------------------------- #


def test_parse_frontmatter_extracts_meta() -> None:
    text = "---\nname: Code Review\ndescription: Reviews code\n---\nDo the review.\n"
    meta, body = _parse_frontmatter(text)
    assert meta["name"] == "Code Review"
    assert meta["description"] == "Reviews code"
    assert body == "Do the review."


def test_parse_frontmatter_no_frontmatter() -> None:
    meta, body = _parse_frontmatter("Just content, no frontmatter.")
    assert meta == {}
    assert body == "Just content, no frontmatter."


def test_command_name_slugified() -> None:
    assert _skill("Code Review!").command_name == "code-review"
    assert _skill("   ").command_name == "skill"


# --------------------------------------------------------------------------- #
# discovery
# --------------------------------------------------------------------------- #


def test_discover_all_kinds(tmp_path: Path) -> None:
    skill_dir = tmp_path / ".claude" / "skills" / "reviewer"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: reviewer\ndescription: reviews\n---\nReview body\n"
    )
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "planner.md").write_text("---\nname: planner\n---\nPlan body\n")
    (tmp_path / "AGENTS.md").write_text("# Agents\nRepo-wide instructions.\n")

    skills = discover_skills([tmp_path])
    by_kind = {s.kind: s for s in skills}
    assert set(by_kind) == {"skill", "agent", "agents-md"}
    assert by_kind["skill"].name == "reviewer"
    assert by_kind["skill"].body == "Review body"
    assert by_kind["agent"].name == "planner"


def test_discover_dedupes_across_roots(tmp_path: Path) -> None:
    for sub in ("project", "home"):
        d = tmp_path / sub / ".claude" / "skills" / "dup"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: dup\n---\nbody\n")
    skills = discover_skills([tmp_path / "project", tmp_path / "home"])
    assert len([s for s in skills if s.command_name == "dup"]) == 1


def test_discover_empty(tmp_path: Path) -> None:
    assert discover_skills([tmp_path]) == []


def test_build_skills_context() -> None:
    ctx = build_skills_context([_skill("Reviewer"), _skill("Planner", kind="agent")])
    assert "/reviewer" in ctx
    assert "/planner" in ctx
    assert build_skills_context([]) == ""


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_skill_command_returns_body() -> None:
    cmd = SkillCommand(_skill("Reviewer", body="step one"))
    assert cmd.name == "reviewer"
    result = await cmd.execute({})
    assert result.success
    assert result.data is not None
    assert result.data["body"] == "step one"


def test_skills_command_parse_arguments() -> None:
    cmd = SkillsCommand([])
    assert cmd.parse_arguments("") == {"action": "list", "name": ""}
    assert cmd.parse_arguments("show reviewer") == {
        "action": "show",
        "name": "reviewer",
    }
    assert cmd.parse_arguments("reviewer") == {"action": "show", "name": "reviewer"}
    assert cmd.parse_arguments("reload")["action"] == "reload"


@pytest.mark.asyncio
async def test_skills_command_list_and_show() -> None:
    skills = [_skill("Reviewer", body="rbody"), _skill("Planner", kind="agent")]
    cmd = SkillsCommand(skills)

    listed = await cmd.execute({"action": "list", "name": ""})
    assert listed.success and "2 skill" in (listed.message or "")

    shown = await cmd.execute({"action": "show", "name": "reviewer"})
    assert shown.success and "Reviewer" in (shown.message or "")

    missing = await cmd.execute({"action": "show", "name": "nope"})
    assert not missing.success


@pytest.mark.asyncio
async def test_skills_command_empty() -> None:
    cmd = SkillsCommand([])
    result = await cmd.execute({"action": "list", "name": ""})
    assert result.success
    assert "No skills" in (result.message or "")
