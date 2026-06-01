"""Tests for cancelling an in-flight streaming response (Escape).

Drives the TUI cancel helpers directly (no real keypresses): a running message
task can be cancelled mid-stream, partial text is preserved, and the app returns
to a ready state without exiting.
"""

from __future__ import annotations

import asyncio

import pytest

from gerdsenai_cli.ui.prompt_toolkit_tui import PromptToolkitTUI


@pytest.fixture
def tui() -> PromptToolkitTUI:
    return PromptToolkitTUI()


def test_not_streaming_by_default(tui: PromptToolkitTUI) -> None:
    assert tui._is_streaming() is False


def test_is_streaming_true_while_streaming(tui: PromptToolkitTUI) -> None:
    tui.conversation.start_streaming("assistant")
    assert tui._is_streaming() is True
    tui.conversation.finish_streaming()
    assert tui._is_streaming() is False


def test_cancel_with_no_active_task_is_noop(tui: PromptToolkitTUI) -> None:
    assert tui._active_message_task is None
    assert tui._cancel_active_message() is False


@pytest.mark.asyncio
async def test_cancel_active_message_cancels_running_task(
    tui: PromptToolkitTUI,
) -> None:
    started = asyncio.Event()

    async def long_running() -> None:
        started.set()
        await asyncio.sleep(10)  # would hang without cancellation

    tui._active_message_task = asyncio.ensure_future(long_running())
    await started.wait()
    task = tui._active_message_task  # capture before cancel clears the handle

    cancelled = tui._cancel_active_message()
    assert cancelled is True

    with pytest.raises(asyncio.CancelledError):
        await task
    assert task.cancelled()


@pytest.mark.asyncio
async def test_cancel_preserves_partial_streamed_text(tui: PromptToolkitTUI) -> None:
    """Finalizing after cancel keeps the partial text in history."""
    tui.conversation.start_streaming("assistant")
    tui.conversation.append_streaming("partial answer so")
    tui.conversation.append_streaming(" far")

    # Simulate the main loop's CancelledError branch: append the inline cancel
    # marker to the partial text, then finalize.
    tui.append_streaming_chunk("\n\n_⏹ Response cancelled._")
    tui.finish_streaming_response()

    # messages are (role, content, timestamp) tuples; partial text + the cancel
    # marker land together in visible history.
    contents = [content for (_role, content, *_rest) in tui.conversation.messages]
    assert any(
        "partial answer so far" in c and "Response cancelled" in c for c in contents
    )
    # Streaming state is cleared; a second finalize is a no-op (no crash).
    assert tui._is_streaming() is False
    tui.finish_streaming_response()


@pytest.mark.asyncio
async def test_completed_task_is_not_cancelled(tui: PromptToolkitTUI) -> None:
    async def quick() -> None:
        return None

    tui._active_message_task = asyncio.ensure_future(quick())
    await tui._active_message_task  # let it finish
    # Nothing to cancel once done.
    assert tui._cancel_active_message() is False


@pytest.mark.asyncio
async def test_cancel_clears_task_reference(tui: PromptToolkitTUI) -> None:
    """After a successful cancel the handle is cleared (no stale double-cancel)."""
    started = asyncio.Event()

    async def long_running() -> None:
        started.set()
        await asyncio.sleep(10)

    tui._active_message_task = asyncio.ensure_future(long_running())
    await started.wait()
    task = tui._active_message_task

    assert tui._cancel_active_message() is True
    assert tui._active_message_task is None  # reference cleared
    # A second cancel is a no-op (nothing stale to act on).
    assert tui._cancel_active_message() is False

    with pytest.raises(asyncio.CancelledError):
        await task
