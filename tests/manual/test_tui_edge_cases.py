"""
Manual TUI Edge Case Testing Script.

This script provides comprehensive manual testing scenarios for the TUI.
Run this to verify all edge cases are handled properly.

Usage:
    python tests/manual/test_tui_edge_cases.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gerdsenai_cli.ui.tui_edge_cases import (
    ConversationMemoryManager,
    InputSanitizer,
    ProviderFailureHandler,
    StreamRecoveryHandler,
    TUIEdgeCaseHandler,
    TUIStateGuard,
)
from gerdsenai_cli.core.errors import GerdsenAIError, ErrorCategory


class TestResult:
    """Track test results."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def pass_test(self, name: str):
        """Record passing test."""
        self.passed += 1
        print(f"✅ {name}")

    def fail_test(self, name: str, error: str):
        """Record failing test."""
        self.failed += 1
        self.errors.append(f"{name}: {error}")
        print(f"❌ {name}: {error}")

    def summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        print("\n" + "=" * 70)
        print(f"Test Summary: {self.passed}/{total} passed")
        if self.failed > 0:
            print(f"\nFailed tests:")
            for error in self.errors:
                print(f"  - {error}")
        print("=" * 70)


async def test_state_guard():
    """Test TUI state guard."""
    results = TestResult()
    print("\n🔒 Testing TUI State Guard")
    print("-" * 70)

    guard = TUIStateGuard()

    # Test 1: Can accept input initially
    allowed, reason = guard.can_accept_input()
    if allowed:
        results.pass_test("Initial state accepts input")
    else:
        results.fail_test("Initial state accepts input", reason)

    # Test 2: Cannot accept input while streaming
    guard.mark_streaming_start()
    allowed, reason = guard.can_accept_input()
    if not allowed and "streaming" in reason.lower():
        results.pass_test("Blocks input during streaming")
    else:
        results.fail_test("Blocks input during streaming", "Should block")

    guard.mark_streaming_end()

    # Test 3: Cannot accept input while processing
    guard.mark_processing_start()
    allowed, reason = guard.can_accept_input()
    if not allowed and "processing" in reason.lower():
        results.pass_test("Blocks input during processing")
    else:
        results.fail_test("Blocks input during processing", "Should block")

    guard.mark_processing_end()

    # Test 4: Rapid-fire protection
    guard.mark_processing_start()
    guard.mark_processing_end()
    allowed, reason = guard.can_accept_input()
    if not allowed and "wait" in reason.lower():
        results.pass_test("Blocks rapid-fire messages")
    else:
        results.fail_test("Blocks rapid-fire messages", "Should enforce delay")

    # Wait to clear delay
    await asyncio.sleep(0.2)

    # Test 5: Lock protection
    counter = []

    async def increment():
        await asyncio.sleep(0.1)
        counter.append(1)

    # Run 3 operations concurrently
    await asyncio.gather(
        guard.with_lock(increment, "op1"),
        guard.with_lock(increment, "op2"),
        guard.with_lock(increment, "op3"),
    )

    if len(counter) == 3:
        results.pass_test("Lock protects concurrent operations")
    else:
        results.fail_test("Lock protects concurrent operations", f"Got {len(counter)} executions")

    results.summary()


async def test_memory_manager():
    """Test conversation memory manager."""
    results = TestResult()
    print("\n💾 Testing Conversation Memory Manager")
    print("-" * 70)

    manager = ConversationMemoryManager(
        max_messages=100,
        max_total_chars=10000,
        archive_threshold=80
    )

    # Test 1: Small conversation doesn't trigger archive
    small_messages = [("user", "test", None) for _ in range(50)]
    if not manager.should_archive(small_messages):
        results.pass_test("Small conversation not archived")
    else:
        results.fail_test("Small conversation not archived", "Should not archive")

    # Test 2: Large message count triggers archive
    large_messages = [("user", "test", None) for _ in range(85)]
    if manager.should_archive(large_messages):
        results.pass_test("Large message count triggers archive")
    else:
        results.fail_test("Large message count triggers archive", "Should archive")

    # Test 3: Large total chars triggers archive
    huge_messages = [("user", "x" * 500, None) for _ in range(25)]
    if manager.should_archive(huge_messages):
        results.pass_test("Large total chars triggers archive")
    else:
        results.fail_test("Large total chars triggers archive", "Should archive")

    # Test 4: Archive keeps recent messages
    messages_to_archive = [("user", f"msg{i}", None) for i in range(150)]
    trimmed, archived = manager.archive_old_messages(messages_to_archive, keep_recent=50)

    if len(trimmed) == 50 and archived == 100:
        results.pass_test("Archive keeps correct number of recent messages")
    else:
        results.fail_test(
            "Archive keeps correct number of recent messages",
            f"Got {len(trimmed)} messages, {archived} archived"
        )

    # Test 5: Archive notice formatting
    notice = manager.get_archive_notice()
    if "100" in notice and "archived" in notice.lower():
        results.pass_test("Archive notice formatted correctly")
    else:
        results.fail_test("Archive notice formatted correctly", f"Got: {notice}")

    results.summary()


async def test_stream_recovery():
    """Test stream recovery handler."""
    results = TestResult()
    print("\n🔄 Testing Stream Recovery Handler")
    print("-" * 70)

    handler = StreamRecoveryHandler(timeout_seconds=5.0)

    # Test 1: Initial health check passes
    is_healthy, error = handler.check_health()
    if is_healthy and error is None:
        results.pass_test("Initial health check passes")
    else:
        results.fail_test("Initial health check passes", f"Got: {error}")

    # Test 2: Stream tracking works
    handler.start_stream()
    for _ in range(10):
        handler.record_chunk()

    if handler.chunks_received == 10:
        results.pass_test("Stream chunk tracking works")
    else:
        results.fail_test("Stream chunk tracking works", f"Got {handler.chunks_received} chunks")

    # Test 3: Health check detects timeout
    handler2 = StreamRecoveryHandler(timeout_seconds=0.1)
    handler2.start_stream()
    await asyncio.sleep(0.2)
    is_healthy, error = handler2.check_health()

    if not is_healthy and "timeout" in error.lower():
        results.pass_test("Detects stream timeout")
    else:
        results.fail_test("Detects stream timeout", f"Got: {error}")

    # Test 4: Recovery message formatting
    recovery_msg = handler.get_recovery_message("Test error")
    if "Stream Interrupted" in recovery_msg and "Recovery options" in recovery_msg:
        results.pass_test("Recovery message formatted correctly")
    else:
        results.fail_test("Recovery message formatted correctly", "Missing expected content")

    results.summary()


async def test_input_sanitizer():
    """Test input sanitizer."""
    results = TestResult()
    print("\n🧹 Testing Input Sanitizer")
    print("-" * 70)

    sanitizer = InputSanitizer()

    # Test 1: Valid input passes
    try:
        sanitized, warnings = sanitizer.sanitize_user_message("Hello, world!")
        if "Hello" in sanitized and len(warnings) == 0:
            results.pass_test("Valid input sanitized correctly")
        else:
            results.fail_test("Valid input sanitized correctly", f"Got: {sanitized}, warnings: {warnings}")
    except Exception as e:
        results.fail_test("Valid input sanitized correctly", str(e))

    # Test 2: Empty input rejected
    try:
        sanitizer.sanitize_user_message("")
        results.fail_test("Empty input rejected", "Should raise error")
    except GerdsenAIError as e:
        if e.category == ErrorCategory.INVALID_REQUEST:
            results.pass_test("Empty input rejected")
        else:
            results.fail_test("Empty input rejected", f"Wrong error category: {e.category}")

    # Test 3: Whitespace-only input rejected
    try:
        sanitizer.sanitize_user_message("   \n\t   ")
        results.fail_test("Whitespace-only input rejected", "Should raise error")
    except GerdsenAIError:
        results.pass_test("Whitespace-only input rejected")

    # Test 4: Large message warning
    try:
        large_message = "x" * 60000
        sanitized, warnings = sanitizer.sanitize_user_message(large_message)
        if len(warnings) > 0 and "Large message" in warnings[0]:
            results.pass_test("Large message warning shown")
        else:
            results.fail_test("Large message warning shown", f"Got warnings: {warnings}")
    except Exception as e:
        results.fail_test("Large message warning shown", str(e))

    # Test 5: Repeated characters warning
    try:
        repeated = "a" * 60
        sanitized, warnings = sanitizer.sanitize_user_message(repeated)
        if any("repeated" in w.lower() for w in warnings):
            results.pass_test("Repeated characters warning shown")
        else:
            results.fail_test("Repeated characters warning shown", f"Got warnings: {warnings}")
    except Exception as e:
        results.fail_test("Repeated characters warning shown", str(e))

    # Test 6: Null bytes rejected
    try:
        sanitizer.sanitize_user_message("Hello\x00world")
        results.fail_test("Null bytes rejected", "Should raise error")
    except GerdsenAIError:
        results.pass_test("Null bytes rejected")

    # Test 7: Dangerous patterns rejected
    try:
        sanitizer.sanitize_user_message("test; rm -rf /")
        results.fail_test("Dangerous patterns rejected", "Should raise error")
    except GerdsenAIError:
        results.pass_test("Dangerous patterns rejected")

    # Test 8: Command argument sanitization
    arg = sanitizer.sanitize_command_arg("  /path/to/file  ")
    if arg == "/path/to/file":
        results.pass_test("Command argument sanitized")
    else:
        results.fail_test("Command argument sanitized", f"Got: {arg}")

    # Test 9: Long command argument truncated
    long_arg = "x" * 2000
    sanitized_arg = sanitizer.sanitize_command_arg(long_arg)
    if len(sanitized_arg) == 1000:
        results.pass_test("Long command argument truncated")
    else:
        results.fail_test("Long command argument truncated", f"Got length: {len(sanitized_arg)}")

    results.summary()


async def test_provider_failure_handler():
    """Test provider failure handler."""
    results = TestResult()
    print("\n🔌 Testing Provider Failure Handler")
    print("-" * 70)

    handler = ProviderFailureHandler()

    # Test 1: Initial state
    if handler.consecutive_failures == 0 and not handler.should_show_recovery_help():
        results.pass_test("Initial state correct")
    else:
        results.fail_test("Initial state correct", f"Got {handler.consecutive_failures} failures")

    # Test 2: Record failures
    for _ in range(3):
        handler.record_failure()

    if handler.consecutive_failures == 3:
        results.pass_test("Failure tracking works")
    else:
        results.fail_test("Failure tracking works", f"Got {handler.consecutive_failures}")

    # Test 3: Show recovery help after 3 failures
    if handler.should_show_recovery_help():
        results.pass_test("Recovery help shown after 3 failures")
    else:
        results.fail_test("Recovery help shown after 3 failures", "Should show help")

    # Test 4: Success resets counter
    handler.record_success()
    if handler.consecutive_failures == 0:
        results.pass_test("Success resets failure counter")
    else:
        results.fail_test("Success resets failure counter", f"Got {handler.consecutive_failures}")

    # Test 5: Recovery message formatting
    from gerdsenai_cli.core.errors import NetworkError
    error = NetworkError(message="Connection failed", host="localhost")

    handler.record_failure()
    handler.record_failure()
    handler.record_failure()

    recovery_msg = handler.get_recovery_message(error)
    if "Provider Error" in recovery_msg and "consecutive failures" in recovery_msg:
        results.pass_test("Recovery message formatted correctly")
    else:
        results.fail_test("Recovery message formatted correctly", "Missing expected content")

    results.summary()


async def test_edge_case_handler_integration():
    """Test TUI edge case handler integration."""
    results = TestResult()
    print("\n🎯 Testing TUI Edge Case Handler Integration")
    print("-" * 70)

    handler = TUIEdgeCaseHandler()

    # Test 1: Validate valid input
    try:
        sanitized, warnings = await handler.validate_and_process_input("Hello, world!")
        if "Hello" in sanitized:
            results.pass_test("Valid input processed")
        else:
            results.fail_test("Valid input processed", f"Got: {sanitized}")
    except Exception as e:
        results.fail_test("Valid input processed", str(e))

    # Test 2: Reject input while streaming
    handler.state_guard.mark_streaming_start()
    try:
        await handler.validate_and_process_input("Test")
        results.fail_test("Reject input while streaming", "Should raise error")
    except GerdsenAIError as e:
        if "streaming" in str(e).lower():
            results.pass_test("Reject input while streaming")
        else:
            results.fail_test("Reject input while streaming", f"Wrong error: {e}")

    handler.state_guard.mark_streaming_end()

    # Test 3: Diagnostics provide useful info
    diagnostics = handler.get_diagnostics()
    required_keys = [
        "is_streaming",
        "is_processing",
        "is_waiting_approval",
        "archived_messages",
        "consecutive_failures"
    ]

    if all(key in diagnostics for key in required_keys):
        results.pass_test("Diagnostics provide complete info")
    else:
        missing = [k for k in required_keys if k not in diagnostics]
        results.fail_test("Diagnostics provide complete info", f"Missing keys: {missing}")

    results.summary()


async def run_all_tests():
    """Run all TUI edge case tests."""
    print("\n" + "=" * 70)
    print("🧪 GerdsenAI TUI Edge Case Testing Suite")
    print("=" * 70)

    await test_state_guard()
    await test_memory_manager()
    await test_stream_recovery()
    await test_input_sanitizer()
    await test_provider_failure_handler()
    await test_edge_case_handler_integration()

    print("\n" + "=" * 70)
    print("✨ All test suites completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
