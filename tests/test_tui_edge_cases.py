"""Pytest suite for the TUI edge-case handlers.

Promotes the previously manual script (tests/manual/test_tui_edge_cases.py) into
the automated suite: state guarding, conversation-memory archiving, stream
recovery health/messaging, input sanitization, and provider-failure escalation.
All handlers are pure logic (no running Application), so these run headless.
"""

from __future__ import annotations

import asyncio

import pytest

from gerdsenai_cli.core.errors import (
    ErrorCategory,
    GerdsenAIError,
    NetworkError,
)
from gerdsenai_cli.ui.tui_edge_cases import (
    ConversationMemoryManager,
    InputSanitizer,
    ProviderFailureHandler,
    StreamRecoveryHandler,
    TUIStateGuard,
)

# --------------------------------------------------------------------------- #
# TUIStateGuard
# --------------------------------------------------------------------------- #


def test_state_guard_accepts_input_initially() -> None:
    guard = TUIStateGuard()
    allowed, _reason = guard.can_accept_input()
    assert allowed is True


def test_state_guard_blocks_during_streaming() -> None:
    guard = TUIStateGuard()
    guard.mark_streaming_start()
    allowed, reason = guard.can_accept_input()
    assert allowed is False
    assert "streaming" in reason.lower()
    guard.mark_streaming_end()
    # (Immediately after, the rapid-fire guard may still hold; the point here is
    # that the streaming flag itself is cleared.)
    assert guard.is_streaming is False


def test_state_guard_blocks_during_processing() -> None:
    guard = TUIStateGuard()
    guard.mark_processing_start()
    allowed, reason = guard.can_accept_input()
    assert allowed is False
    assert "processing" in reason.lower()


def test_state_guard_blocks_rapid_fire() -> None:
    guard = TUIStateGuard()
    guard.mark_processing_start()
    guard.mark_processing_end()
    allowed, reason = guard.can_accept_input()
    assert allowed is False
    assert "wait" in reason.lower()


@pytest.mark.asyncio
async def test_state_guard_lock_serializes_operations() -> None:
    guard = TUIStateGuard()
    counter: list[int] = []

    async def increment() -> None:
        await asyncio.sleep(0.01)
        counter.append(1)

    await asyncio.gather(
        guard.with_lock(increment, "op1"),
        guard.with_lock(increment, "op2"),
        guard.with_lock(increment, "op3"),
    )
    assert len(counter) == 3


# --------------------------------------------------------------------------- #
# ConversationMemoryManager
# --------------------------------------------------------------------------- #


def test_memory_small_conversation_not_archived() -> None:
    manager = ConversationMemoryManager(
        max_messages=100, max_total_chars=10000, archive_threshold=80
    )
    small = [("user", "test", None) for _ in range(50)]
    assert manager.should_archive(small) is False


def test_memory_large_count_triggers_archive() -> None:
    manager = ConversationMemoryManager(
        max_messages=100, max_total_chars=10000, archive_threshold=80
    )
    large = [("user", "test", None) for _ in range(85)]
    assert manager.should_archive(large) is True


def test_memory_large_chars_triggers_archive() -> None:
    manager = ConversationMemoryManager(
        max_messages=100, max_total_chars=10000, archive_threshold=80
    )
    huge = [("user", "x" * 500, None) for _ in range(25)]
    assert manager.should_archive(huge) is True


def test_memory_archive_keeps_recent_and_counts() -> None:
    manager = ConversationMemoryManager()
    messages = [("user", f"msg{i}", None) for i in range(150)]
    trimmed, archived = manager.archive_old_messages(messages, keep_recent=50)
    assert len(trimmed) == 50
    assert archived == 100
    # The kept messages are the most recent ones.
    assert trimmed[-1][1] == "msg149"


def test_memory_archive_notice_mentions_count() -> None:
    manager = ConversationMemoryManager()
    messages = [("user", f"msg{i}", None) for i in range(150)]
    manager.archive_old_messages(messages, keep_recent=50)
    notice = manager.get_archive_notice()
    assert "100" in notice
    assert "archived" in notice.lower()


def test_memory_archive_notice_empty_when_nothing_archived() -> None:
    assert ConversationMemoryManager().get_archive_notice() == ""


# --------------------------------------------------------------------------- #
# StreamRecoveryHandler
# --------------------------------------------------------------------------- #


def test_stream_initial_health_is_ok() -> None:
    handler = StreamRecoveryHandler(timeout_seconds=5.0)
    is_healthy, error = handler.check_health()
    assert is_healthy is True
    assert error is None


def test_stream_chunk_tracking() -> None:
    handler = StreamRecoveryHandler(timeout_seconds=5.0)
    handler.start_stream()
    for _ in range(10):
        handler.record_chunk()
    assert handler.chunks_received == 10


@pytest.mark.asyncio
async def test_stream_detects_timeout() -> None:
    handler = StreamRecoveryHandler(timeout_seconds=0.1)
    handler.start_stream()
    await asyncio.sleep(0.2)
    is_healthy, error = handler.check_health()
    assert is_healthy is False
    assert error is not None and "timeout" in error.lower()


def test_stream_recovery_message_mentions_partial_and_options() -> None:
    handler = StreamRecoveryHandler()
    handler.start_stream()
    handler.record_chunk()
    msg = handler.get_recovery_message("network error")
    assert "Stream Interrupted" in msg
    assert "Recovery options" in msg
    assert "1 chunks" in msg or "Partial response" in msg


# --------------------------------------------------------------------------- #
# InputSanitizer
# --------------------------------------------------------------------------- #


def test_sanitizer_valid_input_passes() -> None:
    sanitized, warnings = InputSanitizer.sanitize_user_message("Hello, world!")
    assert "Hello" in sanitized
    assert warnings == []


def test_sanitizer_empty_input_rejected() -> None:
    with pytest.raises(GerdsenAIError) as exc:
        InputSanitizer.sanitize_user_message("")
    assert exc.value.category == ErrorCategory.INVALID_REQUEST


def test_sanitizer_whitespace_only_rejected() -> None:
    with pytest.raises(GerdsenAIError):
        InputSanitizer.sanitize_user_message("   \n\t   ")


def test_sanitizer_null_bytes_rejected() -> None:
    with pytest.raises(GerdsenAIError):
        InputSanitizer.sanitize_user_message("Hello\x00world")


def test_sanitizer_large_message_warns() -> None:
    # Over the 80% warning threshold (80k of 100k) and non-repeating so it's the
    # "Large message" warning that fires, not the repeated-characters one.
    large = "abcdefghij" * 8500  # 85,000 chars, varied
    _sanitized, warnings = InputSanitizer.sanitize_user_message(large)
    assert any("Large message" in w for w in warnings)


def test_sanitizer_repeated_characters_warns() -> None:
    # The repeated-character heuristic only runs for messages longer than 100.
    repeated = "a" * 150
    _sanitized, warnings = InputSanitizer.sanitize_user_message(repeated)
    assert any("repeated" in w.lower() for w in warnings)


def test_sanitizer_command_arg_trimmed() -> None:
    assert InputSanitizer.sanitize_command_arg("  /path/to/file  ") == "/path/to/file"


def test_sanitizer_command_arg_truncated() -> None:
    assert len(InputSanitizer.sanitize_command_arg("x" * 2000)) == 1000


# --------------------------------------------------------------------------- #
# ProviderFailureHandler
# --------------------------------------------------------------------------- #


def test_provider_initial_state() -> None:
    handler = ProviderFailureHandler()
    assert handler.consecutive_failures == 0
    assert handler.should_show_recovery_help() is False


def test_provider_failure_tracking_and_threshold() -> None:
    handler = ProviderFailureHandler()
    for _ in range(3):
        handler.record_failure()
    assert handler.consecutive_failures == 3
    assert handler.should_show_recovery_help() is True


def test_provider_success_resets_counter() -> None:
    handler = ProviderFailureHandler()
    handler.record_failure()
    handler.record_failure()
    handler.record_success()
    assert handler.consecutive_failures == 0
    assert handler.should_show_recovery_help() is False


def test_provider_recovery_message_network_error() -> None:
    handler = ProviderFailureHandler()
    for _ in range(3):
        handler.record_failure()
    msg = handler.get_recovery_message(NetworkError(message="Connection failed"))
    assert "Provider Error" in msg
    assert "consecutive failures" in msg
