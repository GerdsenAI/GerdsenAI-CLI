"""
Comprehensive TUI Edge Case Handler.

Handles all edge cases, error scenarios, and polishing for the TUI:
- Input validation and sanitization
- Stream interruption handling
- Network timeout recovery
- Provider failure graceful degradation
- Memory management for large conversations
- Concurrent operation protection
- File operation validation
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

from ..core.errors import (
    ErrorCategory,
    ErrorSeverity,
    GerdsenAIError,
    NetworkError,
)
from ..core.errors import (
    TimeoutError as GerdsenAITimeoutError,
)
from ..utils.validation import InputValidator

logger = logging.getLogger(__name__)


class TUIStateGuard:
    """
    Protect TUI from invalid state transitions.

    Prevents concurrent operations, validates state changes,
    and ensures TUI always stays in a valid state.
    """

    def __init__(self):
        self.is_streaming = False
        self.is_processing = False
        self.is_waiting_approval = False
        self.operation_lock = asyncio.Lock()
        self.last_operation_time: Optional[datetime] = None

    def can_accept_input(self) -> tuple[bool, str]:
        """
        Check if TUI can accept new input.

        Returns:
            (allowed, reason) tuple
        """
        if self.is_streaming:
            return False, "AI is currently streaming a response. Please wait."

        if self.is_processing:
            return False, "Processing previous message. Please wait."

        # Check for rapid-fire messages (< 100ms apart)
        if self.last_operation_time:
            time_since_last = datetime.now() - self.last_operation_time
            if time_since_last < timedelta(milliseconds=100):
                return False, "Please wait before sending another message."

        return True, ""

    def mark_streaming_start(self):
        """Mark that streaming has started."""
        self.is_streaming = True
        self.last_operation_time = datetime.now()

    def mark_streaming_end(self):
        """Mark that streaming has ended."""
        self.is_streaming = False

    def mark_processing_start(self):
        """Mark that processing has started."""
        self.is_processing = True
        self.last_operation_time = datetime.now()

    def mark_processing_end(self):
        """Mark that processing has ended."""
        self.is_processing = False

    async def with_lock(self, operation: Callable, operation_name: str = "operation"):
        """
        Execute operation with lock protection.

        Args:
            operation: Async function to execute
            operation_name: Name for logging

        Returns:
            Operation result
        """
        async with self.operation_lock:
            logger.debug(f"Executing locked operation: {operation_name}")
            return await operation()


class ConversationMemoryManager:
    """
    Manage conversation history to prevent memory issues.

    Automatically archives old messages and enforces limits.
    """

    def __init__(
        self,
        max_messages: int = 1000,
        max_total_chars: int = 1_000_000,  # 1MB
        archive_threshold: int = 800,
    ):
        """
        Initialize memory manager.

        Args:
            max_messages: Maximum messages to keep in memory
            max_total_chars: Maximum total characters across all messages
            archive_threshold: Archive when message count exceeds this
        """
        self.max_messages = max_messages
        self.max_total_chars = max_total_chars
        self.archive_threshold = archive_threshold
        self.archived_count = 0

    def should_archive(self, messages: list) -> bool:
        """
        Check if conversation should be archived.

        Args:
            messages: Current message list

        Returns:
            True if archiving needed
        """
        if len(messages) >= self.archive_threshold:
            return True

        # Check total character count
        total_chars = sum(len(content) for _, content, _ in messages)
        if total_chars >= self.max_total_chars:
            return True

        return False

    def archive_old_messages(
        self, messages: list, keep_recent: int = 100
    ) -> tuple[list, int]:
        """
        Archive old messages, keeping recent ones.

        Args:
            messages: Current message list
            keep_recent: Number of recent messages to keep

        Returns:
            (trimmed_messages, archived_count) tuple
        """
        if len(messages) <= keep_recent:
            return messages, 0

        # Keep most recent messages
        archived = len(messages) - keep_recent
        trimmed = messages[-keep_recent:]

        self.archived_count += archived
        logger.info(f"Archived {archived} messages, keeping {keep_recent} recent")

        return trimmed, archived

    def get_archive_notice(self) -> str:
        """
        Get formatted notice about archived messages.

        Returns:
            Archive notice text
        """
        if self.archived_count == 0:
            return ""

        return f"\n📦 {self.archived_count} older messages archived to save memory.\n"


class StreamRecoveryHandler:
    """
    Handle interrupted or failed streams gracefully.

    Detects stream failures and provides recovery options.
    """

    def __init__(self, timeout_seconds: float = 120.0):
        """
        Initialize stream recovery handler.

        Args:
            timeout_seconds: Timeout for stream operations
        """
        self.timeout_seconds = timeout_seconds
        self.stream_start_time: Optional[datetime] = None
        self.chunks_received = 0
        self.last_chunk_time: Optional[datetime] = None

    def start_stream(self):
        """Mark stream start."""
        self.stream_start_time = datetime.now()
        self.chunks_received = 0
        self.last_chunk_time = datetime.now()

    def record_chunk(self):
        """Record that a chunk was received."""
        self.chunks_received += 1
        self.last_chunk_time = datetime.now()

    def check_health(self) -> tuple[bool, Optional[str]]:
        """
        Check stream health.

        Returns:
            (is_healthy, error_message) tuple
        """
        if not self.stream_start_time:
            return True, None

        now = datetime.now()

        # Check total timeout
        elapsed = (now - self.stream_start_time).total_seconds()
        if elapsed > self.timeout_seconds:
            return False, f"Stream timeout ({elapsed:.1f}s > {self.timeout_seconds}s)"

        # Check for stalled stream (no chunks in 30s)
        if self.last_chunk_time:
            since_last_chunk = (now - self.last_chunk_time).total_seconds()
            if since_last_chunk > 30.0:
                return False, f"Stream stalled (no data for {since_last_chunk:.1f}s)"

        return True, None

    def get_recovery_message(self, error: str) -> str:
        """
        Get recovery message for stream failure.

        Args:
            error: Error description

        Returns:
            Formatted recovery message
        """
        msg = f"⚠️  Stream Interrupted: {error}\n\n"

        if self.chunks_received > 0:
            msg += f"Received {self.chunks_received} chunks before interruption.\n"
            msg += "Partial response displayed above.\n\n"

        msg += "Recovery options:\n"
        msg += "  • Try sending your message again\n"
        msg += "  • Check your network connection\n"
        msg += "  • Verify LLM provider is running\n"
        msg += "  • Use /debug to enable detailed logging\n"

        return msg


class InputSanitizer:
    """
    Sanitize and validate user input for TUI.

    Prevents injection attacks, validates length, and handles edge cases.
    """

    @staticmethod
    def sanitize_user_message(message: str) -> tuple[str, list[str]]:
        """
        Sanitize user message input.

        Args:
            message: Raw user input

        Returns:
            (sanitized_message, warnings) tuple
        """
        warnings = []

        # Check for empty or whitespace-only
        if not message or not message.strip():
            raise GerdsenAIError(
                message="Message cannot be empty",
                category=ErrorCategory.INVALID_REQUEST,
                severity=ErrorSeverity.LOW,
                recoverable=True,
            )

        # Validate using InputValidator
        try:
            sanitized = InputValidator.validate_user_input(
                message, max_length=InputValidator.MAX_MESSAGE_LENGTH
            )
        except GerdsenAIError:
            # Re-raise validation errors
            raise

        # Check for extremely long messages (warn at 80% of limit)
        max_len = InputValidator.MAX_MESSAGE_LENGTH
        warning_threshold = int(max_len * 0.8)  # 80KB for 100KB limit

        if len(message) > warning_threshold:
            warnings.append(
                f"⚠️  Large message ({len(message):,} chars, approaching {max_len:,} limit). "
                f"Consider breaking into smaller messages."
            )

        # Check for repeated characters (possible paste error)
        if len(message) > 100:
            # Look for 50+ repeated characters
            for i in range(len(message) - 50):
                if len(set(message[i : i + 50])) == 1:
                    warnings.append(
                        "⚠️  Detected repeated characters. Did you paste correctly?"
                    )
                    break

        # Check for null bytes or control characters
        if "\x00" in message:
            raise GerdsenAIError(
                message="Invalid characters in message",
                category=ErrorCategory.INVALID_REQUEST,
                severity=ErrorSeverity.MEDIUM,
                recoverable=False,
            )

        return sanitized, warnings

    @staticmethod
    def sanitize_command_arg(arg: str) -> str:
        """
        Sanitize command argument.

        Args:
            arg: Command argument

        Returns:
            Sanitized argument
        """
        # Remove any null bytes
        cleaned = arg.replace("\x00", "")

        # Limit length
        if len(cleaned) > 1000:
            cleaned = cleaned[:1000]

        return cleaned.strip()

    @staticmethod
    def sanitize_file_path(path: str) -> Path:
        """
        Sanitize and validate file path.

        Args:
            path: File path string

        Returns:
            Validated Path object
        """
        return InputValidator.validate_file_path(
            path, must_exist=False, must_be_file=True, allow_absolute_only=False
        )


class ProviderFailureHandler:
    """
    Handle provider failures gracefully.

    Provides fallback suggestions and recovery options.
    """

    def __init__(self):
        self.consecutive_failures = 0
        self.last_failure_time: Optional[datetime] = None

    def record_failure(self):
        """Record a provider failure."""
        self.consecutive_failures += 1
        self.last_failure_time = datetime.now()

    def record_success(self):
        """Record a provider success."""
        self.consecutive_failures = 0
        self.last_failure_time = None

    def should_show_recovery_help(self) -> bool:
        """
        Check if we should show recovery help.

        Returns:
            True if help should be shown
        """
        return self.consecutive_failures >= 3

    def get_recovery_message(self, error: Exception) -> str:
        """
        Get recovery message for provider failure.

        Args:
            error: The exception that occurred

        Returns:
            Formatted recovery message
        """
        msg = "❌ Provider Error\n\n"

        # Categorize the error
        if isinstance(error, NetworkError):
            msg += "Network error detected.\n\n"
            msg += "Troubleshooting:\n"
            msg += "  1. Check your network connection\n"
            msg += "  2. Verify the LLM provider URL is correct\n"
            msg += "  3. Ensure the provider is running\n"
            msg += "  4. Check firewall settings\n"

        elif isinstance(error, GerdsenAITimeoutError):
            msg += "Request timed out.\n\n"
            msg += "Troubleshooting:\n"
            msg += "  1. Try a smaller message\n"
            msg += "  2. Check if provider is overloaded\n"
            msg += "  3. Increase timeout in settings\n"
            msg += "  4. Try a different model\n"

        else:
            msg += f"Error: {str(error)}\n\n"
            msg += "General troubleshooting:\n"
            msg += "  1. Restart the LLM provider\n"
            msg += "  2. Check provider logs\n"
            msg += "  3. Verify model is loaded\n"
            msg += "  4. Try /model to select different model\n"

        if self.consecutive_failures >= 3:
            msg += f"\n⚠️  {self.consecutive_failures} consecutive failures detected.\n"
            msg += "Consider switching providers or restarting the LLM server.\n"

        return msg


class TUIEdgeCaseHandler:
    """
    Master edge case handler for TUI.

    Coordinates all edge case handling components.
    """

    def __init__(self):
        self.state_guard = TUIStateGuard()
        self.memory_manager = ConversationMemoryManager()
        self.stream_recovery = StreamRecoveryHandler()
        self.input_sanitizer = InputSanitizer()
        self.provider_handler = ProviderFailureHandler()

    async def validate_and_process_input(
        self, user_input: str
    ) -> tuple[str, list[str]]:
        """
        Validate and process user input.

        Args:
            user_input: Raw user input

        Returns:
            (sanitized_input, warnings) tuple

        Raises:
            GerdsenAIError: If input is invalid
        """
        # Check if TUI can accept input
        allowed, reason = self.state_guard.can_accept_input()
        if not allowed:
            raise GerdsenAIError(
                message=reason,
                category=ErrorCategory.INVALID_REQUEST,
                severity=ErrorSeverity.LOW,
                recoverable=True,
            )

        # Sanitize input
        sanitized, warnings = self.input_sanitizer.sanitize_user_message(user_input)

        return sanitized, warnings

    def manage_conversation_memory(
        self, messages: list, tui_conversation: Any
    ) -> Optional[str]:
        """
        Manage conversation memory to prevent issues.

        Args:
            messages: Current message list
            tui_conversation: TUI conversation object

        Returns:
            Archive notice if messages were archived, None otherwise
        """
        if self.memory_manager.should_archive(messages):
            # Archive old messages
            trimmed, archived = self.memory_manager.archive_old_messages(messages)

            # Update conversation
            tui_conversation.messages = trimmed
            tui_conversation._update_buffer()

            # Return notice
            return self.memory_manager.get_archive_notice()

        return None

    async def handle_stream_with_recovery(
        self, stream_operation: Callable, tui, operation_name: str = "stream"
    ):
        """
        Execute stream operation with recovery handling.

        Args:
            stream_operation: Async function that yields stream chunks
            tui: TUI instance
            operation_name: Name for logging
        """
        self.stream_recovery.start_stream()
        self.state_guard.mark_streaming_start()

        try:
            tui.start_streaming_response()

            async for chunk in stream_operation():
                # Record chunk
                self.stream_recovery.record_chunk()

                # Check health
                is_healthy, error = self.stream_recovery.check_health()
                if not is_healthy:
                    logger.error(f"Stream health check failed: {error}")
                    raise GerdsenAITimeoutError(
                        message=f"Stream failed: {error}",
                        timeout_seconds=self.stream_recovery.timeout_seconds,
                    )

                # Append chunk
                tui.append_streaming_chunk(chunk)

                # Small delay for smooth streaming
                await asyncio.sleep(tui.streaming_chunk_delay)

            # Success
            tui.finish_streaming_response()
            self.provider_handler.record_success()

        except Exception as e:
            # Stream failed
            self.provider_handler.record_failure()

            # Get recovery message
            recovery_msg = self.stream_recovery.get_recovery_message(str(e))

            # Finish streaming with error
            tui.finish_streaming_response()

            # Add recovery message
            if self.provider_handler.should_show_recovery_help():
                provider_recovery = self.provider_handler.get_recovery_message(e)
                recovery_msg += "\n" + provider_recovery

            tui.conversation.add_message("system", recovery_msg)
            tui.app.invalidate()

            raise

        finally:
            self.state_guard.mark_streaming_end()

    def get_diagnostics(self) -> dict[str, Any]:
        """
        Get diagnostic information about TUI state.

        Returns:
            Dictionary with diagnostic data
        """
        return {
            "is_streaming": self.state_guard.is_streaming,
            "is_processing": self.state_guard.is_processing,
            "is_waiting_approval": self.state_guard.is_waiting_approval,
            "last_operation": self.state_guard.last_operation_time.isoformat()
            if self.state_guard.last_operation_time
            else None,
            "archived_messages": self.memory_manager.archived_count,
            "consecutive_failures": self.provider_handler.consecutive_failures,
            "stream_chunks_received": self.stream_recovery.chunks_received,
        }
