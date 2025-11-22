"""
Rate limiting for LLM requests.

This module provides rate limiting to prevent overwhelming local AI servers
and ensure stable performance.
"""

import asyncio
import logging
import time
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for LLM requests.

    Features:
    - Configurable requests per second
    - Burst capacity
    - Async/await support
    - Per-operation rate limits
    """

    def __init__(
        self,
        requests_per_second: float = 2.0,
        burst_size: int = 5,
        per_operation_limits: dict[str, float] | None = None,
    ):
        """
        Initialize the rate limiter.

        Args:
            requests_per_second: Maximum requests per second
            burst_size: Maximum burst size (tokens)
            per_operation_limits: Optional per-operation rate limits (operation -> rps)
        """
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.per_operation_limits = per_operation_limits or {}

        # Token bucket state
        self._tokens = float(burst_size)
        self._last_update = time.time()
        self._lock = asyncio.Lock()

        # Request tracking
        self._request_times: deque[float] = deque(maxlen=100)
        self._total_requests = 0
        self._total_wait_time = 0.0

    async def acquire(self, operation: str = "default", tokens: int = 1) -> None:
        """
        Acquire permission to make a request.

        This method will block (await) until a token is available.

        Args:
            operation: Operation name (for per-operation limits)
            tokens: Number of tokens to acquire (default 1)
        """
        # Get operation-specific rate limit if available
        rate = self.per_operation_limits.get(operation, self.requests_per_second)

        async with self._lock:
            # Refill tokens based on time elapsed
            now = time.time()
            elapsed = now - self._last_update
            self._tokens = min(self.burst_size, self._tokens + elapsed * rate)
            self._last_update = now

            # Wait if not enough tokens
            wait_time = 0.0
            while self._tokens < tokens:
                # Calculate how long to wait
                tokens_needed = tokens - self._tokens
                wait_time = tokens_needed / rate
                logger.debug(f"Rate limit: waiting {wait_time:.2f}s for {operation}")

                # Release lock while waiting
                self._lock.release()
                await asyncio.sleep(wait_time)
                async with self._lock:
                    pass  # Re-acquire lock
                self._lock = asyncio.Lock()  # Reset lock state

                # Refill tokens
                now = time.time()
                elapsed = now - self._last_update
                self._tokens = min(self.burst_size, self._tokens + elapsed * rate)
                self._last_update = now

            # Consume tokens
            self._tokens -= tokens

            # Track statistics
            self._request_times.append(now)
            self._total_requests += 1
            self._total_wait_time += wait_time

    async def try_acquire(self, operation: str = "default", tokens: int = 1) -> bool:
        """
        Try to acquire permission without blocking.

        Args:
            operation: Operation name
            tokens: Number of tokens to acquire

        Returns:
            True if acquired, False if would need to wait
        """
        rate = self.per_operation_limits.get(operation, self.requests_per_second)

        async with self._lock:
            # Refill tokens
            now = time.time()
            elapsed = now - self._last_update
            self._tokens = min(self.burst_size, self._tokens + elapsed * rate)
            self._last_update = now

            # Check if enough tokens
            if self._tokens >= tokens:
                self._tokens -= tokens
                self._request_times.append(now)
                self._total_requests += 1
                return True
            else:
                return False

    def get_current_rate(self) -> float:
        """
        Get the current request rate (requests per second).

        Returns:
            Current rate in requests/second
        """
        if len(self._request_times) < 2:
            return 0.0

        # Calculate rate over last N requests
        time_span = self._request_times[-1] - self._request_times[0]
        if time_span > 0:
            return len(self._request_times) / time_span
        return 0.0

    def get_stats(self) -> dict[str, Any]:
        """
        Get rate limiter statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "total_requests": self._total_requests,
            "total_wait_time": self._total_wait_time,
            "current_rate": self.get_current_rate(),
            "max_rate": self.requests_per_second,
            "available_tokens": self._tokens,
            "burst_size": self.burst_size,
        }

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._request_times.clear()
        self._total_requests = 0
        self._total_wait_time = 0.0


# Global rate limiter instance
_global_limiter: RateLimiter | None = None


def get_rate_limiter(
    requests_per_second: float = 2.0,
    burst_size: int = 5,
    per_operation_limits: dict[str, float] | None = None,
) -> RateLimiter:
    """
    Get or create the global rate limiter instance.

    Args:
        requests_per_second: Maximum requests per second
        burst_size: Maximum burst size
        per_operation_limits: Per-operation rate limits

    Returns:
        Global RateLimiter instance
    """
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter(
            requests_per_second=requests_per_second,
            burst_size=burst_size,
            per_operation_limits=per_operation_limits,
        )
    return _global_limiter
