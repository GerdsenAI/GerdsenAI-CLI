"""Headless one-shot mode: gerdsenai -p runs one turn, prints the answer, exits."""
from __future__ import annotations

import pytest

import gerdsenai_cli.utils.display as display
from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.main import GerdsenAICLI


@pytest.fixture(autouse=True)
def _restore_console():
    """run_headless flips display to a stderr console; restore it after each test
    so the module-global swap never leaks into other tests."""
    original = display.console
    yield
    display.console = original


@pytest.mark.asyncio
async def test_run_headless_prints_answer_and_returns_zero(monkeypatch, tmp_path, capsys):
    """run_headless initializes, runs one turn, prints the answer, exits 0"""
    monkeypatch.setenv("HOME", str(tmp_path))  # keep any config/conversation I/O hermetic
    cli = GerdsenAICLI(config_path=None, interactive=False)

    class _FakeAgent:
        def __init__(self) -> None:
            self.settings = Settings(current_model="fake-model")
            self.cleaned = False

        async def process_user_input(self, text: str) -> str:
            return f"answer:{text}"

        async def cleanup(self) -> None:
            self.cleaned = True

    class _FakeClient:
        async def __aexit__(self, *exc) -> None:
            return None

    fake_agent = _FakeAgent()

    async def _fake_init() -> bool:
        cli.settings = fake_agent.settings
        cli.agent = fake_agent
        cli.llm_client = _FakeClient()
        return True

    monkeypatch.setattr(cli, "initialize", _fake_init)

    code = await cli.run_headless("hello fleet")

    assert code == 0
    assert "answer:hello fleet" in capsys.readouterr().out
    assert fake_agent.cleaned is True


@pytest.mark.asyncio
async def test_run_headless_returns_one_when_init_fails(monkeypatch, tmp_path):
    """If initialization fails, run_headless returns exit code 1 without raising"""
    monkeypatch.setenv("HOME", str(tmp_path))
    cli = GerdsenAICLI(config_path=None, interactive=False)

    async def _fail_init() -> bool:
        return False

    monkeypatch.setattr(cli, "initialize", _fail_init)
    assert await cli.run_headless("anything") == 1


@pytest.mark.asyncio
async def test_run_headless_returns_one_when_no_model(monkeypatch, tmp_path):
    """No current_model after init -> fail fast with exit 1 (no cryptic empty-model call)"""
    monkeypatch.setenv("HOME", str(tmp_path))
    cli = GerdsenAICLI(config_path=None, interactive=False)

    class _FakeAgent:
        def __init__(self) -> None:
            self.settings = Settings(current_model="")  # nothing selected
            self.called = False

        async def process_user_input(self, text: str) -> str:
            self.called = True
            return "should not run"

        async def cleanup(self) -> None:
            return None

    class _FakeClient:
        async def __aexit__(self, *exc) -> None:
            return None

    fake_agent = _FakeAgent()

    async def _fake_init() -> bool:
        cli.settings = fake_agent.settings
        cli.agent = fake_agent
        cli.llm_client = _FakeClient()
        return True

    monkeypatch.setattr(cli, "initialize", _fake_init)

    code = await cli.run_headless("hello")
    assert code == 1
    assert fake_agent.called is False  # never dispatched with an empty model
