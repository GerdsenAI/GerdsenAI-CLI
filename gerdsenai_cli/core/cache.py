"""
Request caching for LLM responses.

This module provides intelligent caching of LLM requests to reduce redundant API calls
and improve response times for repeated queries.
"""

import hashlib
import json
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from cachetools import TTLCache

logger = logging.getLogger(__name__)

# Type variable for generic function return types
T = TypeVar("T")


class LLMCache:
    """
    Intelligent caching for LLM requests.

    Features:
    - TTL-based expiration (default 1 hour)
    - Size-limited (default 100 entries)
    - Content-based hashing
    - Cache statistics tracking
    """

    def __init__(self, maxsize: int = 100, ttl: int = 3600):
        """
        Initialize the LLM cache.

        Args:
            maxsize: Maximum number of cache entries
            ttl: Time-to-live for cache entries in seconds (default 1 hour)
        """
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._hits = 0
        self._misses = 0
        self._total_saved_time = 0.0

    def _compute_key(
        self, messages: list[dict[str, str]], model: str, temperature: float
    ) -> str:
        """
        Compute a cache key for the request.

        Args:
            messages: List of chat messages
            model: Model name
            temperature: Temperature parameter

        Returns:
            SHA256 hash of the request
        """
        # Create a deterministic representation
        key_data = {
            "model": model,
            "temperature": temperature,
            "messages": messages,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
    ) -> tuple[bool, Any]:
        """
        Get a cached response if available.

        Args:
            messages: List of chat messages
            model: Model name
            temperature: Temperature parameter

        Returns:
            (hit, response) tuple - hit is True if cache hit, response is cached value or None
        """
        # Don't cache high-temperature requests (non-deterministic)
        if temperature > 0.5:
            self._misses += 1
            return False, None

        key = self._compute_key(messages, model, temperature)

        if key in self._cache:
            self._hits += 1
            cached_entry = self._cache[key]
            self._total_saved_time += cached_entry.get("inference_time", 0.0)
            logger.debug(
                f"Cache HIT for key {key[:16]}... (saved ~{cached_entry.get('inference_time', 0):.2f}s)"
            )
            return True, cached_entry["response"]
        else:
            self._misses += 1
            logger.debug(f"Cache MISS for key {key[:16]}...")
            return False, None

    def put(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        response: Any,
        inference_time: float = 0.0,
    ) -> None:
        """
        Store a response in the cache.

        Args:
            messages: List of chat messages
            model: Model name
            temperature: Temperature parameter
            response: Response to cache
            inference_time: Time taken for inference (for stats)
        """
        # Don't cache high-temperature requests
        if temperature > 0.5:
            return

        key = self._compute_key(messages, model, temperature)
        self._cache[key] = {
            "response": response,
            "inference_time": inference_time,
            "cached_at": time.time(),
        }
        logger.debug(
            f"Cached response for key {key[:16]}... (saved {inference_time:.2f}s)"
        )

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.info("Cache cleared")

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "cache_size": len(self._cache),
            "max_size": self._cache.maxsize,
            "total_saved_time": self._total_saved_time,
        }

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self._hits = 0
        self._misses = 0
        self._total_saved_time = 0.0


# Global cache instance
_global_cache: LLMCache | None = None


def get_cache(maxsize: int = 100, ttl: int = 3600) -> LLMCache:
    """
    Get or create the global cache instance.

    Args:
        maxsize: Maximum number of cache entries
        ttl: Time-to-live for cache entries in seconds

    Returns:
        Global LLMCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = LLMCache(maxsize=maxsize, ttl=ttl)
    return _global_cache


def cached_llm_request(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to cache LLM requests.

    Usage:
        @cached_llm_request
        async def chat_completion(self, messages, model, temperature):
            ...
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract caching parameters
        messages = kwargs.get("messages") or (args[1] if len(args) > 1 else None)
        model = kwargs.get("model") or (args[2] if len(args) > 2 else None)
        temperature = kwargs.get("temperature", 0.7)

        if messages is None or model is None:
            # Can't cache without messages and model
            return await func(*args, **kwargs)

        cache = get_cache()

        # Check cache
        hit, cached_response = cache.get(messages, model, temperature)
        if hit:
            return cached_response

        # Execute request
        start_time = time.time()
        response = await func(*args, **kwargs)
        inference_time = time.time() - start_time

        # Cache response
        cache.put(messages, model, temperature, response, inference_time)

        return response

    return wrapper
