"""
Tests for token counting with tiktoken.

Comprehensive test coverage for the token_counter module.
"""

import pytest

from gerdsenai_cli.core.token_counter import (
    TIKTOKEN_AVAILABLE,
    TokenCounter,
    count_messages_tokens,
    count_tokens,
    estimate_max_response_tokens,
    estimate_tokens_heuristic,
    get_encoding,
    get_token_counter,
    truncate_messages_to_fit,
)


class TestTokenCounting:
    """Tests for basic token counting functions."""

    def test_estimate_tokens_heuristic_empty(self):
        """Test heuristic estimation with empty string."""
        assert estimate_tokens_heuristic("") == 0

    def test_estimate_tokens_heuristic_basic(self):
        """Test heuristic estimation with basic text."""
        # "Hello world" is 11 chars, ~3 tokens
        text = "Hello world"
        tokens = estimate_tokens_heuristic(text)
        assert tokens == len(text) // 4

    def test_estimate_tokens_heuristic_long_text(self):
        """Test heuristic estimation with long text."""
        text = "A" * 1000
        tokens = estimate_tokens_heuristic(text)
        assert tokens == 250  # 1000 / 4

    def test_count_tokens_empty(self):
        """Test count_tokens with empty string."""
        assert count_tokens("") == 0

    def test_count_tokens_basic(self):
        """Test count_tokens with basic text."""
        text = "Hello, world!"
        tokens = count_tokens(text)
        assert tokens > 0
        # Should be reasonable (2-5 tokens for this text)
        assert 1 <= tokens <= 10

    def test_count_tokens_long_text(self):
        """Test count_tokens with long text."""
        text = "Hello " * 100
        tokens = count_tokens(text)
        assert tokens > 100  # Should be more than 100 tokens

    def test_count_tokens_code(self):
        """Test count_tokens with code."""
        code = """
def hello():
    print("Hello, world!")
    return 42
"""
        tokens = count_tokens(code)
        assert tokens > 0

    def test_count_tokens_different_models(self):
        """Test count_tokens with different model names."""
        text = "Hello, world!"

        tokens_llama = count_tokens(text, "llama-2-7b")
        tokens_gpt = count_tokens(text, "gpt-4")
        tokens_default = count_tokens(text, "unknown-model")

        # All should give reasonable counts
        assert tokens_llama > 0
        assert tokens_gpt > 0
        assert tokens_default > 0

    @pytest.mark.skipif(not TIKTOKEN_AVAILABLE, reason="tiktoken not installed")
    def test_get_encoding_caching(self):
        """Test that encoding is cached."""
        enc1 = get_encoding("gpt-4")
        enc2 = get_encoding("gpt-4")
        assert enc1 is enc2  # Should be same object (cached)

    @pytest.mark.skipif(not TIKTOKEN_AVAILABLE, reason="tiktoken not installed")
    def test_get_encoding_different_models(self):
        """Test getting encodings for different models."""
        enc_llama = get_encoding("llama-2-7b")
        enc_gpt = get_encoding("gpt-4")
        assert enc_llama is not None
        assert enc_gpt is not None


class TestMessageTokenCounting:
    """Tests for message token counting."""

    def test_count_messages_tokens_empty(self):
        """Test counting tokens in empty message list."""
        tokens = count_messages_tokens([])
        assert tokens == 3  # Conversation overhead

    def test_count_messages_tokens_single_message(self):
        """Test counting tokens in single message."""
        messages = [{"role": "user", "content": "Hello"}]
        tokens = count_messages_tokens(messages)
        assert tokens > 0
        # Should include content + role + formatting overhead
        assert tokens >= 5  # At least some tokens

    def test_count_messages_tokens_multiple_messages(self):
        """Test counting tokens in multiple messages."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        tokens = count_messages_tokens(messages)
        assert tokens > 10  # Multiple messages should have decent token count

    def test_count_messages_tokens_long_content(self):
        """Test counting tokens in messages with long content."""
        messages = [{"role": "user", "content": "Hello " * 1000}]
        tokens = count_messages_tokens(messages)
        assert tokens > 500  # Long content should result in many tokens

    def test_count_messages_tokens_with_model(self):
        """Test counting tokens with specific model."""
        messages = [{"role": "user", "content": "Hello"}]
        tokens_llama = count_messages_tokens(messages, "llama-2-7b")
        tokens_gpt = count_messages_tokens(messages, "gpt-4")

        # Both should give reasonable counts
        assert tokens_llama > 0
        assert tokens_gpt > 0


class TestMaxResponseTokens:
    """Tests for estimating max response tokens."""

    def test_estimate_max_response_tokens_empty(self):
        """Test with empty messages."""
        max_tokens = estimate_max_response_tokens(
            messages=[],
            context_window=4096,
            context_usage=0.8,
        )
        # Should have most of the context available
        assert max_tokens > 0
        assert max_tokens < 4096

    def test_estimate_max_response_tokens_basic(self):
        """Test with basic messages."""
        messages = [{"role": "user", "content": "Hello"}]
        max_tokens = estimate_max_response_tokens(
            messages=messages,
            context_window=4096,
            context_usage=0.8,
        )
        # Should have plenty of space for response
        assert max_tokens > 1000

    def test_estimate_max_response_tokens_large_context(self):
        """Test with large context."""
        messages = [{"role": "user", "content": "Hello " * 1000}]
        max_tokens = estimate_max_response_tokens(
            messages=messages,
            context_window=4096,
            context_usage=0.8,
        )
        # Should have less space
        assert max_tokens >= 0
        assert max_tokens < 4096

    def test_estimate_max_response_tokens_exceeds_window(self):
        """Test when messages exceed context window."""
        messages = [{"role": "user", "content": "Hello " * 10000}]
        max_tokens = estimate_max_response_tokens(
            messages=messages,
            context_window=4096,
            context_usage=0.8,
        )
        # Should return 0 or very small number
        assert max_tokens >= 0

    def test_estimate_max_response_tokens_custom_usage(self):
        """Test with custom context usage."""
        messages = [{"role": "user", "content": "Hello"}]

        # Low usage (more for response)
        max_low = estimate_max_response_tokens(
            messages=messages,
            context_window=4096,
            context_usage=0.5,
        )

        # High usage (less for response)
        max_high = estimate_max_response_tokens(
            messages=messages,
            context_window=4096,
            context_usage=0.9,
        )

        # Low usage should give more tokens for response
        assert max_low > max_high


class TestMessageTruncation:
    """Tests for truncating messages to fit context."""

    def test_truncate_messages_empty(self):
        """Test truncating empty message list."""
        result = truncate_messages_to_fit(
            messages=[],
            context_window=4096,
            context_usage=0.8,
        )
        assert result == []

    def test_truncate_messages_fits(self):
        """Test when messages fit within context."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]
        result = truncate_messages_to_fit(
            messages=messages,
            context_window=4096,
            context_usage=0.8,
        )
        assert len(result) == 2
        assert result == messages

    def test_truncate_messages_needs_truncation(self):
        """Test when messages need truncation."""
        messages = [
            {"role": "user", "content": "Message " + str(i)}
            for i in range(100)
        ]
        result = truncate_messages_to_fit(
            messages=messages,
            context_window=1000,  # Small context
            context_usage=0.8,
        )
        # Should keep only recent messages
        assert len(result) < len(messages)
        # Should keep most recent
        assert result[-1] == messages[-1]

    def test_truncate_messages_preserves_system(self):
        """Test that system message is preserved."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            *[{"role": "user", "content": "Message " + str(i)} for i in range(50)],
        ]
        result = truncate_messages_to_fit(
            messages=messages,
            context_window=1000,
            context_usage=0.8,
        )
        # System message should always be first
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "You are a helpful assistant."

    def test_truncate_messages_recent_priority(self):
        """Test that recent messages are prioritized."""
        messages = [
            {"role": "user", "content": "Old message"},
            {"role": "user", "content": "Recent message"},
        ]
        result = truncate_messages_to_fit(
            messages=messages,
            context_window=100,  # Very small
            context_usage=0.8,
        )
        # Should keep recent message
        if len(result) > 0:
            assert "Recent message" in result[-1]["content"]


class TestTokenCounter:
    """Tests for TokenCounter class."""

    def test_initialization_default(self):
        """Test TokenCounter initialization."""
        counter = TokenCounter()
        assert counter.model == "default"
        assert counter.cache_size == 256
        assert len(counter._cache) == 0

    def test_initialization_custom(self):
        """Test TokenCounter with custom parameters."""
        counter = TokenCounter(model="llama-2-7b", cache_size=100)
        assert counter.model == "llama-2-7b"
        assert counter.cache_size == 100

    def test_count_with_caching(self):
        """Test counting with caching."""
        counter = TokenCounter()
        text = "Hello, world!"

        # First count
        tokens1 = counter.count(text)
        assert tokens1 > 0
        assert text in counter._cache

        # Second count (should use cache)
        tokens2 = counter.count(text)
        assert tokens2 == tokens1

    def test_count_different_texts(self):
        """Test counting different texts."""
        counter = TokenCounter()

        tokens1 = counter.count("Hello")
        tokens2 = counter.count("Goodbye")

        assert tokens1 > 0
        assert tokens2 > 0
        assert len(counter._cache) == 2

    def test_cache_size_limit(self):
        """Test that cache respects size limit."""
        counter = TokenCounter(cache_size=5)

        # Add more than cache size
        for i in range(10):
            counter.count(f"Text {i}")

        # Cache should not exceed size
        assert len(counter._cache) <= 5

    def test_count_messages(self):
        """Test counting messages."""
        counter = TokenCounter()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]

        tokens = counter.count_messages(messages)
        assert tokens > 0

    def test_clear_cache(self):
        """Test clearing cache."""
        counter = TokenCounter()
        counter.count("Hello")
        counter.count("World")

        assert len(counter._cache) == 2

        counter.clear_cache()
        assert len(counter._cache) == 0


class TestGlobalTokenCounter:
    """Tests for global token counter instance."""

    def test_get_token_counter_singleton(self):
        """Test that get_token_counter returns singleton for same model."""
        counter1 = get_token_counter("llama-2-7b")
        counter2 = get_token_counter("llama-2-7b")
        assert counter1 is counter2

    def test_get_token_counter_different_models(self):
        """Test different models get different counters."""
        get_token_counter("llama-2-7b")
        counter2 = get_token_counter("gpt-4")
        # Second call updates the singleton
        assert counter2.model == "gpt-4"


class TestTokenCounterPerformance:
    """Performance tests for token counter."""

    def test_count_performance(self):
        """Test counting performance."""
        counter = TokenCounter()
        text = "Hello, world! " * 100

        import time
        start = time.time()
        for _ in range(100):
            counter.count(text)
        elapsed = time.time() - start

        # Should be very fast with caching (< 0.1s for 100 counts)
        assert elapsed < 0.5

    def test_cache_effectiveness(self):
        """Test that caching improves performance."""
        counter = TokenCounter()
        text = "Hello, world! " * 100

        import time

        # First count (no cache)
        start = time.time()
        counter.count(text)
        first_elapsed = time.time() - start

        # Subsequent counts (cached)
        start = time.time()
        for _ in range(100):
            counter.count(text)
        cached_elapsed = time.time() - start

        # Cached should be much faster
        assert cached_elapsed < first_elapsed * 10


class TestTokenCounterEdgeCases:
    """Edge case tests for token counter."""

    def test_count_empty_string(self):
        """Test counting empty string."""
        counter = TokenCounter()
        tokens = counter.count("")
        assert tokens == 0

    def test_count_very_long_text(self):
        """Test counting very long text."""
        counter = TokenCounter()
        text = "A" * 100000  # 100K characters
        tokens = counter.count(text)
        assert tokens > 1000

    def test_count_unicode(self):
        """Test counting Unicode text."""
        counter = TokenCounter()
        text = "Hello 世界 🌍"
        tokens = counter.count(text)
        assert tokens > 0

    def test_count_messages_empty_content(self):
        """Test counting messages with empty content."""
        counter = TokenCounter()
        messages = [{"role": "user", "content": ""}]
        tokens = counter.count_messages(messages)
        # Should have some tokens for formatting
        assert tokens > 0

    def test_count_messages_missing_role(self):
        """Test counting messages with missing role."""
        counter = TokenCounter()
        messages = [{"content": "Hello"}]
        tokens = counter.count_messages(messages)
        # Should still count content
        assert tokens > 0
