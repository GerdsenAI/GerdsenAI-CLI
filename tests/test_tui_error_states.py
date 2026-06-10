"""Tests for the TUI stream error/recovery path.

Drives ``TUIEdgeCaseHandler.handle_stream_with_recovery`` — the seam the TUI
uses to run a streamed turn with timeout/health checks and graceful failure —
against a real (headless) ``PromptToolkitTUI`` and fake stream operations that
succeed, raise, or stall. Asserts partial text is preserved, recovery notes are
surfaced through ``system_info``, and the provider-failure threshold escalates.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from gerdsenai_cli.core.errors import NetworkError
from gerdsenai_cli.core.errors import TimeoutError as GerdsenAITimeoutError
from gerdsenai_cli.ui.prompt_toolkit_tui import PromptToolkitTUI
from gerdsenai_cli.ui.tui_edge_cases import TUIEdgeCaseHandler


@pytest.fixture
def tui() -> PromptToolkitTUI:
    return PromptToolkitTUI()


@pytest.fixture
def handler() -> TUIEdgeCaseHandler:
    return TUIEdgeCaseHandler()


def _system_text(tui: PromptToolkitTUI) -> str:
    return tui.conversation.system_info or ""


def _message_contents(tui: PromptToolkitTUI) -> list[str]:
    return [content for (_role, content, *_rest) in tui.conversation.messages]


# --------------------------------------------------------------------------- #
# happy path
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_successful_stream_finalizes_and_resets_failures(
    tui: PromptToolkitTUI, handler: TUIEdgeCaseHandler
) -> None:
    async def good() -> AsyncIterator[str]:
        yield "hello"
        yield " world"

    await handler.handle_stream_with_recovery(good, tui, "test")

    assert any("hello world" in c for c in _message_contents(tui))
    assert handler.provider_handler.consecutive_failures == 0
    # No recovery note on success.
    assert "Stream Interrupted" not in _system_text(tui)
    assert handler.state_guard.is_streaming is False


# --------------------------------------------------------------------------- #
# failure path
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_stream_error_preserves_partial_text_and_adds_recovery(
    tui: PromptToolkitTUI, handler: TUIEdgeCaseHandler
) -> None:
    async def failing() -> AsyncIterator[str]:
        yield "partial answer"
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await handler.handle_stream_with_recovery(failing, tui, "test")

    # Partial text was finalized before the failure note.
    assert any("partial answer" in c for c in _message_contents(tui))
    # A recovery note is surfaced (now visible via system_info rendering).
    assert "Stream Interrupted" in _system_text(tui)
    assert handler.provider_handler.consecutive_failures == 1
    # One failure is below the help threshold: no provider troubleshooting block.
    assert "Provider Error" not in _system_text(tui)
    assert handler.state_guard.is_streaming is False


@pytest.mark.asyncio
async def test_three_failures_escalate_to_provider_recovery(
    tui: PromptToolkitTUI, handler: TUIEdgeCaseHandler
) -> None:
    # Pre-load two prior failures; the third trips the recovery-help threshold.
    handler.provider_handler.record_failure()
    handler.provider_handler.record_failure()

    async def failing() -> AsyncIterator[str]:
        raise NetworkError(message="connection refused")
        yield ""  # pragma: no cover - unreachable, makes this an async generator

    with pytest.raises(NetworkError):
        await handler.handle_stream_with_recovery(failing, tui, "test")

    text = _system_text(tui)
    assert handler.provider_handler.consecutive_failures == 3
    assert "Provider Error" in text
    assert "consecutive failures" in text


@pytest.mark.asyncio
async def test_success_after_failures_resets_counter(
    tui: PromptToolkitTUI, handler: TUIEdgeCaseHandler
) -> None:
    handler.provider_handler.record_failure()
    handler.provider_handler.record_failure()

    async def good() -> AsyncIterator[str]:
        yield "recovered"

    await handler.handle_stream_with_recovery(good, tui, "test")
    assert handler.provider_handler.consecutive_failures == 0


@pytest.mark.asyncio
async def test_stream_timeout_is_detected(
    tui: PromptToolkitTUI, handler: TUIEdgeCaseHandler
) -> None:
    """A stream that outlives the timeout fails the health check and recovers."""
    # Force an effectively-zero timeout so the first health check trips.
    handler.stream_recovery.timeout_seconds = 0.0

    async def slow() -> AsyncIterator[str]:
        yield "first chunk"  # health check runs after this and sees elapsed > 0

    with pytest.raises(GerdsenAITimeoutError):
        await handler.handle_stream_with_recovery(slow, tui, "test")

    assert "Stream Interrupted" in _system_text(tui)
    assert handler.state_guard.is_streaming is False
