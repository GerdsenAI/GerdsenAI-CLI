"""
Tests for LLM request caching.

Comprehensive test coverage for the cache module.
"""

import asyncio
import time

import pytest

from gerdsenai_cli.core.cache import LLMCache, cached_llm_request, get_cache


class TestLLMCache:
    """Tests for LLMCache class."""

    def test_cache_initialization(self):
        """Test cache initialization with default parameters."""
        cache = LLMCache()
        assert cache._cache.maxsize == 100
        assert cache._cache.ttl == 3600
        assert cache._hits == 0
        assert cache._misses == 0

    def test_cache_initialization_custom_params(self):
        """Test cache initialization with custom parameters."""
        cache = LLMCache(maxsize=50, ttl=1800)
        assert cache._cache.maxsize == 50
        assert cache._cache.ttl == 1800

    def test_cache_miss(self):
        """Test cache miss scenario."""
        cache = LLMCache()
        messages = [{"role": "user", "content": "Hello"}]
        model = "test-model"
        temperature = 0.3

        hit, response = cache.get(messages, model, temperature)
        assert not hit
        assert response is None
        assert cache._misses == 1
        assert cache._hits == 0

    def test_cache_hit(self):
        """Test cache hit scenario."""
        cache = LLMCache()
        messages = [{"role": "user", "content": "Hello"}]
        model = "test-model"
        temperature = 0.3
        expected_response = {"choices": [{"message": {"content": "Hi!"}}]}

        # Store response
        cache.put(messages, model, temperature, expected_response, 1.5)

        # Retrieve response
        hit, response = cache.get(messages, model, temperature)
        assert hit
        assert response == expected_response
        assert cache._hits == 1
        assert cache._misses == 0

    def test_cache_high_temperature_not_cached(self):
        """Test that high-temperature requests are not cached."""
        cache = LLMCache()
        messages = [{"role": "user", "content": "Hello"}]
        model = "test-model"
        temperature = 0.8  # High temperature

        # Try to cache
        cache.put(messages, model, temperature, {"content": "test"}, 1.0)

        # Should not be in cache
        hit, response = cache.get(messages, model, temperature)
        assert not hit
        assert cache._misses == 1

    def test_cache_different_messages_different_keys(self):
        """Test that different messages produce different cache keys."""
        cache = LLMCache()
        messages1 = [{"role": "user", "content": "Hello"}]
        messages2 = [{"role": "user", "content": "Goodbye"}]
        model = "test-model"
        temperature = 0.3

        cache.put(messages1, model, temperature, {"response": "1"}, 1.0)
        cache.put(messages2, model, temperature, {"response": "2"}, 1.0)

        hit1, resp1 = cache.get(messages1, model, temperature)
        hit2, resp2 = cache.get(messages2, model, temperature)

        assert hit1 and hit2
        assert resp1["response"] == "1"
        assert resp2["response"] == "2"

    def test_cache_ttl_expiration(self):
        """Test that cache entries expire after TTL."""
        cache = LLMCache(maxsize=100, ttl=1)  # 1 second TTL
        messages = [{"role": "user", "content": "Hello"}]
        model = "test-model"
        temperature = 0.3

        cache.put(messages, model, temperature, {"response": "test"}, 1.0)

        # Should be in cache immediately
        hit, _ = cache.get(messages, model, temperature)
        assert hit

        # Wait for expiration
        time.sleep(1.5)

        # Should be expired
        hit, _ = cache.get(messages, model, temperature)
        assert not hit

    def test_cache_size_limit(self):
        """Test that cache respects size limit."""
        cache = LLMCache(maxsize=2)  # Only 2 entries
        model = "test-model"
        temperature = 0.3

        # Add 3 entries
        for i in range(3):
            messages = [{"role": "user", "content": f"Message {i}"}]
            cache.put(messages, model, temperature, {"response": str(i)}, 1.0)

        # Cache should have only 2 entries (LRU eviction)
        assert len(cache._cache) <= 2

    def test_cache_clear(self):
        """Test cache clearing."""
        cache = LLMCache()
        messages = [{"role": "user", "content": "Hello"}]
        model = "test-model"
        temperature = 0.3

        cache.put(messages, model, temperature, {"response": "test"}, 1.0)
        assert len(cache._cache) == 1

        cache.clear()
        assert len(cache._cache) == 0

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = LLMCache()
        messages = [{"role": "user", "content": "Hello"}]
        model = "test-model"
        temperature = 0.3

        # Miss
        cache.get(messages, model, temperature)

        # Hit
        cache.put(messages, model, temperature, {"response": "test"}, 2.5)
        cache.get(messages, model, temperature)

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total_requests"] == 2
        assert stats["hit_rate"] == 0.5
        assert stats["total_saved_time"] == 2.5

    def test_cache_stats_reset(self):
        """Test resetting cache statistics."""
        cache = LLMCache()
        messages = [{"role": "user", "content": "Hello"}]
        model = "test-model"
        temperature = 0.3

        cache.get(messages, model, temperature)
        cache.reset_stats()

        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["total_saved_time"] == 0.0


class TestGlobalCache:
    """Tests for global cache instance."""

    def test_get_cache_singleton(self):
        """Test that get_cache returns singleton instance."""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2

    def test_get_cache_custom_params(self):
        """Test get_cache with custom parameters."""
        cache = get_cache(maxsize=200, ttl=7200)
        assert cache._cache.maxsize in (100, 200)  # May be singleton


class TestCachedDecorator:
    """Tests for cached_llm_request decorator."""

    @pytest.mark.asyncio
    async def test_cached_decorator_basic(self):
        """Test basic decorator functionality."""
        call_count = 0

        @cached_llm_request
        async def mock_llm_call(messages, model, temperature=0.7):
            nonlocal call_count
            call_count += 1
            return {"response": f"call_{call_count}"}

        # First call - should execute
        result1 = await mock_llm_call(
            messages=[{"role": "user", "content": "test"}],
            model="test-model",
            temperature=0.3
        )
        assert result1["response"] == "call_1"
        assert call_count == 1

        # Second call with same params - should use cache
        result2 = await mock_llm_call(
            messages=[{"role": "user", "content": "test"}],
            model="test-model",
            temperature=0.3
        )
        assert result2["response"] == "call_1"  # Same result
        assert call_count == 1  # Not called again

    @pytest.mark.asyncio
    async def test_cached_decorator_high_temp_not_cached(self):
        """Test that high temperature calls are not cached."""
        call_count = 0

        @cached_llm_request
        async def mock_llm_call(messages, model, temperature=0.7):
            nonlocal call_count
            call_count += 1
            return {"response": f"call_{call_count}"}

        # High temperature calls should not be cached
        result1 = await mock_llm_call(
            messages=[{"role": "user", "content": "test"}],
            model="test-model",
            temperature=0.9
        )
        result2 = await mock_llm_call(
            messages=[{"role": "user", "content": "test"}],
            model="test-model",
            temperature=0.9
        )

        assert result1["response"] == "call_1"
        assert result2["response"] == "call_2"
        assert call_count == 2  # Called both times

    @pytest.mark.asyncio
    async def test_cached_decorator_different_params(self):
        """Test that different parameters result in different cache entries."""
        @cached_llm_request
        async def mock_llm_call(messages, model, temperature=0.7):
            return {"response": f"model_{model}"}

        result1 = await mock_llm_call(
            messages=[{"role": "user", "content": "test"}],
            model="model-1",
            temperature=0.3
        )
        result2 = await mock_llm_call(
            messages=[{"role": "user", "content": "test"}],
            model="model-2",
            temperature=0.3
        )

        assert result1["response"] == "model_model-1"
        assert result2["response"] == "model_model-2"


class TestCachePerformance:
    """Performance tests for cache."""

    def test_cache_key_computation_performance(self):
        """Test that cache key computation is fast."""
        cache = LLMCache()
        messages = [{"role": "user", "content": "Hello " * 100}]  # Long message
        model = "test-model"
        temperature = 0.3

        start = time.time()
        for _ in range(1000):
            cache._compute_key(messages, model, temperature)
        elapsed = time.time() - start

        # Should be very fast (< 100ms for 1000 computations)
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_cache_concurrent_access(self):
        """Test cache with concurrent access."""
        cache = LLMCache()
        messages = [{"role": "user", "content": "test"}]
        model = "test-model"
        temperature = 0.3

        # Pre-populate cache
        cache.put(messages, model, temperature, {"response": "test"}, 1.0)

        # Concurrent reads
        async def read_cache():
            return cache.get(messages, model, temperature)

        results = await asyncio.gather(*[read_cache() for _ in range(100)])

        # All should be hits
        assert all(hit for hit, _ in results)
        assert cache._hits == 100


class TestCacheEdgeCases:
    """Edge case tests for cache."""

    def test_cache_empty_messages(self):
        """Test cache with empty messages."""
        cache = LLMCache()
        messages = []
        model = "test-model"
        temperature = 0.3

        cache.put(messages, model, temperature, {"response": "empty"}, 1.0)
        hit, response = cache.get(messages, model, temperature)

        assert hit
        assert response["response"] == "empty"

    def test_cache_none_response(self):
        """Test caching None response."""
        cache = LLMCache()
        messages = [{"role": "user", "content": "test"}]
        model = "test-model"
        temperature = 0.3

        cache.put(messages, model, temperature, None, 1.0)
        hit, response = cache.get(messages, model, temperature)

        assert hit
        assert response is None

    def test_cache_large_response(self):
        """Test caching large response."""
        cache = LLMCache()
        messages = [{"role": "user", "content": "test"}]
        model = "test-model"
        temperature = 0.3
        large_response = {"content": "A" * 100000}  # 100KB response

        cache.put(messages, model, temperature, large_response, 1.0)
        hit, response = cache.get(messages, model, temperature)

        assert hit
        assert len(response["content"]) == 100000
