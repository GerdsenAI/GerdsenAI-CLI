"""Tests for lazy project scanning.

The project filesystem scan should not run at ``Agent.initialize()`` (so startup
is instant on large repos); it should run on the first turn that needs context,
or eagerly only when the ``eager_project_scan`` preference is set.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.core.agent import Agent
from gerdsenai_cli.core.llm_client import ChatMessage


class FakeLLMClient:
    """Minimal LLM client; records nothing beyond what the scan tests need."""

    async def chat(self, messages: list[ChatMessage], **kwargs: Any) -> str:
        return "ok"

    async def stream_chat(self, messages: list[ChatMessage], **kwargs: Any):
        yield "ok"

    def get_model_context_window(self, model_id: str) -> int:
        return 8192


def _project(tmp_path: Path) -> Path:
    """Create a tiny project tree for scanning."""
    (tmp_path / "a.py").write_text("print('a')\n")
    (tmp_path / "b.py").write_text("print('b')\n")
    return tmp_path


@pytest.mark.asyncio
async def test_initialize_does_not_scan_by_default(tmp_path: Path) -> None:
    """initialize() leaves the file index empty (lazy scan)."""
    _project(tmp_path)
    agent = Agent(FakeLLMClient(), Settings(), project_root=tmp_path)
    ok = await agent.initialize()
    assert ok is True
    assert len(agent.context_manager.files) == 0


@pytest.mark.asyncio
async def test_initialize_eager_scan_when_opted_in(tmp_path: Path) -> None:
    """With eager_project_scan set, initialize() populates the index."""
    _project(tmp_path)
    settings = Settings()
    settings.set_preference("eager_project_scan", True)
    agent = Agent(FakeLLMClient(), settings, project_root=tmp_path)
    await agent.initialize()
    assert len(agent.context_manager.files) > 0


@pytest.mark.asyncio
async def test_first_context_build_triggers_scan(tmp_path: Path) -> None:
    """The lazy scan happens on the first context build."""
    _project(tmp_path)
    agent = Agent(FakeLLMClient(), Settings(), project_root=tmp_path)
    await agent.initialize()
    assert len(agent.context_manager.files) == 0  # still lazy

    await agent._build_project_context("tell me about this project")
    # The scan ran because files was empty when context was built.
    assert len(agent.context_manager.files) > 0
