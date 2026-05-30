"""Discover and load external skill / agent definition files.

Reads, read-only, the agent/skill files that other tools leave in a project so
GerdsenAI can surface them: Claude Code skills (``.claude/skills/*/SKILL.md``),
Claude Code subagents (``.claude/agents/*.md``), and Codex/agent instructions
(``AGENTS.md``). Discovered skills are exposed as slash commands and summarised
into the agent's system prompt.

Frontmatter is parsed with a tiny built-in reader so there is no PyYAML
dependency; only simple ``key: value`` lines are needed (name, description).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_MAX_BODY_CHARS = 20_000
_SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class Skill:
    """An imported skill or agent definition."""

    name: str
    description: str
    body: str
    source: Path
    kind: str  # "skill" | "agent" | "agents-md"

    @property
    def command_name(self) -> str:
        """Slug used as the slash-command name."""
        slug = _SLUG_RE.sub("-", self.name.strip().lower()).strip("-")
        return slug or "skill"


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split optional ``---`` YAML-ish frontmatter from the body.

    Only ``key: value`` lines are understood (sufficient for name/description).
    """
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    meta: dict[str, str] = {}
    body_start = len(lines)
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            body_start = i + 1
            break
        if ":" in lines[i]:
            key, _, value = lines[i].partition(":")
            meta[key.strip().lower()] = value.strip().strip("'\"")
    body = "\n".join(lines[body_start:]).strip()
    return meta, body


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:_MAX_BODY_CHARS]
    except OSError:
        return None


def _load_file(path: Path, kind: str, default_name: str) -> Skill | None:
    text = _read(path)
    if text is None:
        return None
    meta, body = _parse_frontmatter(text)
    name = meta.get("name") or default_name
    description = meta.get("description") or f"Imported {kind} from {path.name}"
    return Skill(name=name, description=description, body=body, source=path, kind=kind)


def default_roots() -> list[Path]:
    """Project directory first (wins on conflicts), then the user's home."""
    return [Path.cwd(), Path.home()]


def discover_skills(roots: list[Path] | None = None) -> list[Skill]:
    """Find skill/agent files under the given roots (read-only).

    De-duplicates by (kind, command_name); earlier roots win.
    """
    roots = roots or default_roots()
    seen: set[tuple[str, str]] = set()
    skills: list[Skill] = []

    def add(skill: Skill | None) -> None:
        if skill is None:
            return
        key = (skill.kind, skill.command_name)
        if key in seen:
            return
        seen.add(key)
        skills.append(skill)

    for root in roots:
        try:
            # Claude Code skills: .claude/skills/<name>/SKILL.md
            for skill_md in sorted(root.glob(".claude/skills/*/SKILL.md")):
                add(_load_file(skill_md, "skill", skill_md.parent.name))
            # Claude Code subagents: .claude/agents/*.md
            for agent_md in sorted(root.glob(".claude/agents/*.md")):
                add(_load_file(agent_md, "agent", agent_md.stem))
            # Codex / generic agent instructions: AGENTS.md
            agents_file = root / "AGENTS.md"
            if agents_file.is_file():
                add(_load_file(agents_file, "agents-md", "agents"))
        except OSError as e:
            logger.debug(f"Skill discovery error under {root}: {e}")

    logger.info(f"Discovered {len(skills)} imported skill/agent file(s)")
    return skills


def build_skills_context(skills: list[Skill], max_entries: int = 25) -> str:
    """Render a compact system-prompt block summarising available skills."""
    if not skills:
        return ""
    lines = [
        "# Imported Skills & Agents",
        "",
        "The following skills/agent guides are available in this project. "
        "Apply the relevant ones; a user can view a skill's full text with "
        "`/skills show <name>` or by running its slash command.",
        "",
    ]
    for skill in skills[:max_entries]:
        lines.append(f"- **/{skill.command_name}** ({skill.kind}): {skill.description}")
    return "\n".join(lines)
