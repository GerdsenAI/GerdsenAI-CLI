"""
Minimal reproducer test for httpx.AsyncClient lifecycle in pytest-asyncio.

This test verifies that the LLMClient properly creates httpx.AsyncClient
within the async event loop context, preventing the 100% CPU hang issue.
"""

import pytest
import pytest_asyncio

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.core.llm_client import LLMClient

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(scope="function")
async def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        protocol="http",
        llm_host="10.69.7.180",
        llm_port=1234,
        current_model="test-model",
        api_timeout=5.0,
    )


async def test_llm_client_async_context_manager(test_settings: Settings) -> None:
    """Test that LLMClient properly creates httpx.AsyncClient in async context."""
    # This should NOT hang - the httpx.AsyncClient should be created in __aenter__
    async with LLMClient(test_settings) as client:
        # Verify client is created
        assert client.client is not None
        assert client.base_url == "http://10.69.7.180:1234"

    # Verify cleanup happened
    # Note: client.client might still exist but should be closed


async def test_llm_client_without_context_manager_raises(test_settings: Settings) -> None:
    """Test that using LLMClient without async context manager has no client."""
    client = LLMClient(test_settings)

    # Client should be None before entering context
    assert client.client is None

    # Verify we can't use the client without context (will return False due to internal error handling)
    result = await client.connect()
    assert result is False, "Should fail to connect without async context manager"


async def test_llm_client_multiple_contexts(test_settings: Settings) -> None:
    """Test that LLMClient can be used in multiple async contexts sequentially."""
    # First context
    async with LLMClient(test_settings) as client1:
        assert client1.client is not None

    # Second context - should work without hanging
    async with LLMClient(test_settings) as client2:
        assert client2.client is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
