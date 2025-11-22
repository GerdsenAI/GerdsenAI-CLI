"""
Tests for LLM request rate limiting.

Comprehensive test coverage for the rate_limiter module.
"""

import asyncio
import time

import pytest

from gerdsenai_cli.core.rate_limiter import RateLimiter, get_rate_limiter


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_initialization_default(self):
        """Test rate limiter initialization with defaults."""
        limiter = RateLimiter()
        assert limiter.requests_per_second == 2.0
        assert limiter.burst_size == 5
        assert limiter._tokens == 5.0
        assert limiter._total_requests == 0

    def test_initialization_custom(self):
        """Test rate limiter initialization with custom parameters."""
        limiter = RateLimiter(requests_per_second=10.0, burst_size=20)
        assert limiter.requests_per_second == 10.0
        assert limiter.burst_size == 20
        assert limiter._tokens == 20.0

    @pytest.mark.asyncio
    async def test_acquire_basic(self):
        """Test basic token acquisition."""
        limiter = RateLimiter(requests_per_second=100.0)  # High rate for fast test
        await limiter.acquire()
        assert limiter._total_requests == 1

    @pytest.mark.asyncio
    async def test_acquire_multiple(self):
        """Test multiple token acquisitions."""
        limiter = RateLimiter(requests_per_second=100.0, burst_size=10)

        for i in range(5):
            await limiter.acquire()

        assert limiter._total_requests == 5

    @pytest.mark.asyncio
    async def test_acquire_rate_limiting(self):
        """Test that rate limiting actually limits requests."""
        limiter = RateLimiter(requests_per_second=10.0, burst_size=2)

        # Exhaust burst
        await limiter.acquire()
        await limiter.acquire()

        # Next acquire should wait
        start = time.time()
        await limiter.acquire()
        elapsed = time.time() - start

        # Should have waited at least ~0.1s (1/10 rps)
        assert elapsed >= 0.05  # Allow some slack

    @pytest.mark.asyncio
    async def test_try_acquire_success(self):
        """Test try_acquire when tokens available."""
        limiter = RateLimiter(requests_per_second=10.0, burst_size=5)

        result = await limiter.try_acquire()
        assert result is True
        assert limiter._total_requests == 1

    @pytest.mark.asyncio
    async def test_try_acquire_failure(self):
        """Test try_acquire when no tokens available."""
        limiter = RateLimiter(requests_per_second=1.0, burst_size=1)

        # Exhaust tokens
        await limiter.acquire()

        # Should fail
        result = await limiter.try_acquire()
        assert result is False

    @pytest.mark.asyncio
    async def test_token_refill(self):
        """Test that tokens refill over time."""
        limiter = RateLimiter(requests_per_second=10.0, burst_size=1)

        # Exhaust tokens
        await limiter.acquire()
        assert limiter._tokens < 1.0

        # Wait for refill
        await asyncio.sleep(0.2)  # Should refill ~2 tokens at 10 rps

        # Should be able to acquire again
        result = await limiter.try_acquire()
        assert result is True

    @pytest.mark.asyncio
    async def test_per_operation_limits(self):
        """Test per-operation rate limits."""
        per_op_limits = {
            "fast": 100.0,
            "slow": 1.0,
        }
        limiter = RateLimiter(
            requests_per_second=10.0,
            burst_size=10,
            per_operation_limits=per_op_limits,
        )

        # Fast operation should be fast
        start = time.time()
        for _ in range(5):
            await limiter.acquire(operation="fast")
        fast_elapsed = time.time() - start

        # Should be very fast (< 0.1s)
        assert fast_elapsed < 0.1

        # Slow operation should wait
        start = time.time()
        await limiter.acquire(operation="slow")
        await limiter.acquire(operation="slow")
        slow_elapsed = time.time() - start

        # Should wait at least ~1s
        assert slow_elapsed >= 0.5

    def test_get_current_rate_empty(self):
        """Test get_current_rate with no requests."""
        limiter = RateLimiter()
        assert limiter.get_current_rate() == 0.0

    @pytest.mark.asyncio
    async def test_get_current_rate_after_requests(self):
        """Test get_current_rate after some requests."""
        limiter = RateLimiter(requests_per_second=100.0)

        # Make some requests
        for _ in range(10):
            await limiter.acquire()

        rate = limiter.get_current_rate()
        assert rate > 0.0

    def test_get_stats(self):
        """Test statistics gathering."""
        limiter = RateLimiter()
        stats = limiter.get_stats()

        assert "total_requests" in stats
        assert "total_wait_time" in stats
        assert "current_rate" in stats
        assert "max_rate" in stats
        assert "available_tokens" in stats
        assert "burst_size" in stats

        assert stats["max_rate"] == 2.0
        assert stats["burst_size"] == 5

    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        """Test that stats are correctly tracked."""
        limiter = RateLimiter(requests_per_second=10.0)

        for _ in range(5):
            await limiter.acquire()

        stats = limiter.get_stats()
        assert stats["total_requests"] == 5

    def test_reset_stats(self):
        """Test statistics reset."""
        limiter = RateLimiter()
        limiter._total_requests = 10
        limiter._total_wait_time = 5.0

        limiter.reset_stats()

        assert limiter._total_requests == 0
        assert limiter._total_wait_time == 0.0
        assert len(limiter._request_times) == 0


class TestGlobalRateLimiter:
    """Tests for global rate limiter instance."""

    def test_get_rate_limiter_singleton(self):
        """Test that get_rate_limiter returns singleton."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2

    def test_get_rate_limiter_custom_params(self):
        """Test get_rate_limiter with custom parameters."""
        limiter = get_rate_limiter(requests_per_second=5.0, burst_size=10)
        # May be singleton, so check existence
        assert limiter is not None


class TestRateLimiterPerformance:
    """Performance tests for rate limiter."""

    @pytest.mark.asyncio
    async def test_high_throughput(self):
        """Test rate limiter with high throughput."""
        limiter = RateLimiter(requests_per_second=1000.0, burst_size=100)

        start = time.time()
        tasks = [limiter.acquire() for _ in range(100)]
        await asyncio.gather(*tasks)
        elapsed = time.time() - start

        # Should be very fast (< 1s for 100 requests at 1000 rps)
        assert elapsed < 1.0

    @pytest.mark.asyncio
    async def test_concurrent_acquire(self):
        """Test concurrent token acquisition."""
        limiter = RateLimiter(requests_per_second=100.0, burst_size=50)

        async def acquire_token():
            await limiter.acquire()

        # Launch many concurrent acquires
        tasks = [acquire_token() for _ in range(50)]
        await asyncio.gather(*tasks)

        assert limiter._total_requests == 50

    @pytest.mark.asyncio
    async def test_sustained_rate(self):
        """Test sustained request rate over time."""
        target_rps = 20.0
        limiter = RateLimiter(requests_per_second=target_rps, burst_size=10)

        requests_made = 0
        duration = 0.5  # seconds
        start = time.time()

        while time.time() - start < duration:
            await limiter.acquire()
            requests_made += 1

        elapsed = time.time() - start
        actual_rps = requests_made / elapsed

        # Should be close to target (within 50%)
        assert target_rps * 0.5 <= actual_rps <= target_rps * 1.5


class TestRateLimiterEdgeCases:
    """Edge case tests for rate limiter."""

    @pytest.mark.asyncio
    async def test_acquire_zero_tokens(self):
        """Test acquiring zero tokens."""
        limiter = RateLimiter()
        await limiter.acquire(tokens=0)
        # Should not consume tokens
        assert limiter._tokens > 0

    @pytest.mark.asyncio
    async def test_acquire_multiple_tokens(self):
        """Test acquiring multiple tokens at once."""
        limiter = RateLimiter(requests_per_second=10.0, burst_size=10)

        await limiter.acquire(tokens=3)
        assert limiter._total_requests == 1
        # Should have consumed 3 tokens
        assert limiter._tokens < 10.0

    @pytest.mark.asyncio
    async def test_very_low_rate(self):
        """Test with very low rate limit."""
        limiter = RateLimiter(requests_per_second=0.5, burst_size=1)

        # First request should be immediate
        start = time.time()
        await limiter.acquire()
        first_elapsed = time.time() - start
        assert first_elapsed < 0.1

        # Second request should wait ~2 seconds
        start = time.time()
        await limiter.acquire()
        second_elapsed = time.time() - start
        assert second_elapsed >= 1.0  # At least 1s wait

    @pytest.mark.asyncio
    async def test_very_high_rate(self):
        """Test with very high rate limit."""
        limiter = RateLimiter(requests_per_second=10000.0, burst_size=1000)

        start = time.time()
        for _ in range(100):
            await limiter.acquire()
        elapsed = time.time() - start

        # Should be nearly instant
        assert elapsed < 0.5

    @pytest.mark.asyncio
    async def test_burst_then_steady(self):
        """Test burst followed by steady rate."""
        limiter = RateLimiter(requests_per_second=10.0, burst_size=20)

        # Burst: should be fast
        start = time.time()
        for _ in range(20):
            await limiter.acquire()
        burst_elapsed = time.time() - start
        assert burst_elapsed < 0.5

        # Steady: should be rate-limited
        start = time.time()
        for _ in range(10):
            await limiter.acquire()
        steady_elapsed = time.time() - start
        # Should take ~1 second at 10 rps
        assert steady_elapsed >= 0.5


class TestRateLimiterIntegration:
    """Integration tests combining multiple features."""

    @pytest.mark.asyncio
    async def test_mixed_operations(self):
        """Test mixing different operations."""
        per_op_limits = {
            "health": 100.0,  # Fast health checks
            "chat": 2.0,  # Slow chat requests
        }
        limiter = RateLimiter(
            requests_per_second=10.0,
            burst_size=10,
            per_operation_limits=per_op_limits,
        )

        # Many health checks should be fast
        start = time.time()
        for _ in range(10):
            await limiter.acquire(operation="health")
        health_elapsed = time.time() - start
        assert health_elapsed < 0.5

        # Few chat requests should be rate-limited
        start = time.time()
        for _ in range(3):
            await limiter.acquire(operation="chat")
        chat_elapsed = time.time() - start
        assert chat_elapsed >= 0.5  # At 2 rps, 3 requests = ~1s

    @pytest.mark.asyncio
    async def test_stats_after_mixed_usage(self):
        """Test statistics after mixed usage."""
        limiter = RateLimiter(requests_per_second=10.0)

        # Some successful acquires
        for _ in range(5):
            await limiter.acquire()

        # Some try_acquires (some may fail)
        for _ in range(5):
            await limiter.try_acquire()

        stats = limiter.get_stats()
        assert stats["total_requests"] >= 5  # At least the successful ones
