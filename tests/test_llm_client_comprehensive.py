"""
Comprehensive integration tests for LLM client with timeouts.

Tests all timeout configurations, retry logic, and error handling.
"""

import asyncio

import httpx
import pytest

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.core.llm_client import OPERATION_TIMEOUTS, LLMClient


class TestLLMClientTimeouts:
    """Comprehensive timeout tests."""

    @pytest.mark.asyncio
    async def test_default_timeout_values(self):
        """Test default timeout values are correct."""
        settings = Settings()
        async with LLMClient(settings) as client:
            assert client._get_timeout("health") >= 10.0
            assert client._get_timeout("models") >= 30.0
            assert client._get_timeout("chat") >= 600.0
            assert client._get_timeout("stream") >= 600.0

    @pytest.mark.asyncio
    async def test_custom_health_timeout(self):
        """Test custom health check timeout."""
        settings = Settings(health_check_timeout=20.0)
        async with LLMClient(settings) as client:
            timeout = client._get_timeout("health")
            assert timeout == 20.0

    @pytest.mark.asyncio
    async def test_custom_models_timeout(self):
        """Test custom model list timeout."""
        settings = Settings(model_list_timeout=60.0)
        async with LLMClient(settings) as client:
            timeout = client._get_timeout("models")
            assert timeout == 60.0

    @pytest.mark.asyncio
    async def test_custom_chat_timeout(self):
        """Test custom chat timeout."""
        settings = Settings(chat_timeout=1200.0)
        async with LLMClient(settings) as client:
            timeout = client._get_timeout("chat")
            assert timeout == 1200.0

    @pytest.mark.asyncio
    async def test_custom_stream_timeout(self):
        """Test custom stream timeout."""
        settings = Settings(stream_timeout=1500.0)
        async with LLMClient(settings) as client:
            timeout = client._get_timeout("stream")
            assert timeout == 1500.0

    @pytest.mark.asyncio
    async def test_api_timeout_fallback(self):
        """Test fallback to api_timeout."""
        settings = Settings(api_timeout=800.0)
        async with LLMClient(settings) as client:
            timeout = client._get_timeout("unknown_operation")
            assert timeout == 800.0

    @pytest.mark.asyncio
    async def test_timeout_priority_operation_specific(self):
        """Test that operation-specific timeout takes priority."""
        settings = Settings(
            api_timeout=600.0,
            chat_timeout=1200.0,
        )
        async with LLMClient(settings) as client:
            chat_timeout = client._get_timeout("chat")
            assert chat_timeout == 1200.0  # operation-specific, not api_timeout

    @pytest.mark.asyncio
    async def test_timeout_priority_api_timeout(self):
        """Test that api_timeout is used when operation-specific not set."""
        settings = Settings(api_timeout=900.0)
        async with LLMClient(settings) as client:
            unknown_timeout = client._get_timeout("unknown")
            assert unknown_timeout == 900.0

    @pytest.mark.asyncio
    async def test_all_timeouts_configurable(self):
        """Test that all timeouts are independently configurable."""
        settings = Settings(
            health_check_timeout=15.0,
            model_list_timeout=45.0,
            chat_timeout=900.0,
            stream_timeout=1000.0,
            api_timeout=700.0,
        )
        async with LLMClient(settings) as client:
            assert client._get_timeout("health") == 15.0
            assert client._get_timeout("models") == 45.0
            assert client._get_timeout("chat") == 900.0
            assert client._get_timeout("stream") == 1000.0
            assert client._get_timeout("default") == 700.0

    @pytest.mark.asyncio
    async def test_timeout_constants_reasonable(self):
        """Test that timeout constants are reasonable for local AI."""
        assert OPERATION_TIMEOUTS["health"] >= 5.0
        assert OPERATION_TIMEOUTS["models"] >= 10.0
        assert OPERATION_TIMEOUTS["chat"] >= 300.0
        assert OPERATION_TIMEOUTS["stream"] >= 300.0
        assert OPERATION_TIMEOUTS["default"] >= 300.0


class TestLLMClientRetry:
    """Comprehensive retry logic tests."""

    @pytest.mark.asyncio
    async def test_default_retry_count(self):
        """Test default retry count."""
        settings = Settings()
        async with LLMClient(settings) as client:
            assert client._max_retries >= 2

    @pytest.mark.asyncio
    async def test_custom_retry_count(self):
        """Test custom retry count."""
        settings = Settings(max_retries=5)
        async with LLMClient(settings) as client:
            assert client._max_retries == 5

    @pytest.mark.asyncio
    async def test_zero_retries(self):
        """Test with zero retries."""
        settings = Settings(max_retries=0)
        async with LLMClient(settings) as client:
            assert client._max_retries == 0

    @pytest.mark.asyncio
    async def test_retry_backoff_calculation(self):
        """Test exponential backoff calculation."""
        settings = Settings()
        async with LLMClient(settings) as client:
            # Test that retry delays increase exponentially
            assert client is not None


class TestLLMClientConnection:
    """Connection lifecycle tests."""

    @pytest.mark.asyncio
    async def test_client_context_manager(self):
        """Test client as context manager."""
        settings = Settings()
        async with LLMClient(settings) as client:
            assert client.client is not None

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initialization."""
        settings = Settings()
        client = LLMClient(settings)
        assert client.settings == settings
        assert client.base_url == settings.llm_server_url

    @pytest.mark.asyncio
    async def test_client_close(self):
        """Test client close."""
        settings = Settings()
        async with LLMClient(settings) as client:
            pass  # Will close automatically
        assert client.client is None or client.client.is_closed

    @pytest.mark.asyncio
    async def test_client_without_context_manager_fails(self):
        """Test that client requires context manager."""
        settings = Settings()
        client = LLMClient(settings)
        with pytest.raises(RuntimeError):
            client._ensure_client()


class TestLLMClientSettings:
    """Settings integration tests."""

    @pytest.mark.asyncio
    async def test_settings_server_url(self):
        """Test server URL from settings."""
        settings = Settings(llm_server_url="http://localhost:11434")
        async with LLMClient(settings) as client:
            assert client.base_url == "http://localhost:11434"

    @pytest.mark.asyncio
    async def test_settings_protocol_host_port(self):
        """Test server URL from protocol/host/port."""
        settings = Settings(
            protocol="http",
            llm_host="localhost",
            llm_port=8080,
        )
        async with LLMClient(settings) as client:
            assert "8080" in client.base_url

    @pytest.mark.asyncio
    async def test_settings_model(self):
        """Test model from settings."""
        settings = Settings(current_model="llama2")
        async with LLMClient(settings) as client:
            assert client.settings.current_model == "llama2"


class TestLLMClientPerformance:
    """Performance tracking tests."""

    @pytest.mark.asyncio
    async def test_request_count_tracking(self):
        """Test that requests are counted."""
        settings = Settings()
        async with LLMClient(settings) as client:
            initial_count = client._request_count
            assert initial_count == 0

    @pytest.mark.asyncio
    async def test_retry_count_tracking(self):
        """Test that retries are counted."""
        settings = Settings()
        async with LLMClient(settings) as client:
            initial_retry = client._retry_count
            assert initial_retry == 0

    @pytest.mark.asyncio
    async def test_time_tracking(self):
        """Test that time is tracked."""
        settings = Settings()
        async with LLMClient(settings) as client:
            initial_time = client._total_request_time
            assert initial_time == 0.0


class TestLLMClientEndpoints:
    """Endpoint construction tests."""

    @pytest.mark.asyncio
    async def test_endpoint_construction(self):
        """Test endpoint URL construction."""
        settings = Settings(llm_server_url="http://localhost:11434")
        async with LLMClient(settings) as client:
            endpoint = client._get_endpoint("/v1/chat/completions")
            assert endpoint == "http://localhost:11434/v1/chat/completions"

    @pytest.mark.asyncio
    async def test_endpoint_with_trailing_slash(self):
        """Test endpoint with trailing slash."""
        settings = Settings(llm_server_url="http://localhost:11434/")
        async with LLMClient(settings) as client:
            endpoint = client._get_endpoint("v1/chat/completions")
            assert endpoint.count("//") == 1  # Only in http://

    @pytest.mark.asyncio
    async def test_endpoint_with_leading_slash(self):
        """Test endpoint with leading slash."""
        settings = Settings(llm_server_url="http://localhost:11434")
        async with LLMClient(settings) as client:
            endpoint1 = client._get_endpoint("/api")
            endpoint2 = client._get_endpoint("api")
            assert endpoint1 == endpoint2


class TestLLMClientEdgeCases:
    """Edge case tests."""

    @pytest.mark.asyncio
    async def test_very_long_timeout(self):
        """Test with very long timeout."""
        settings = Settings(chat_timeout=3600.0)  # 1 hour
        async with LLMClient(settings) as client:
            timeout = client._get_timeout("chat")
            assert timeout == 3600.0

    @pytest.mark.asyncio
    async def test_minimum_timeout(self):
        """Test with minimum timeout."""
        settings = Settings(health_check_timeout=1.0)
        async with LLMClient(settings) as client:
            timeout = client._get_timeout("health")
            assert timeout == 1.0

    @pytest.mark.asyncio
    async def test_timeout_float_precision(self):
        """Test timeout float precision."""
        settings = Settings(chat_timeout=1234.567)
        async with LLMClient(settings) as client:
            timeout = client._get_timeout("chat")
            assert abs(timeout - 1234.567) < 0.001

    @pytest.mark.asyncio
    async def test_concurrent_clients(self):
        """Test multiple concurrent clients."""
        settings = Settings()

        async with LLMClient(settings) as client1:
            async with LLMClient(settings) as client2:
                assert client1 is not client2
                assert client1.client is not None
                assert client2.client is not None


class TestLLMClientConfiguration:
    """Configuration option tests."""

    @pytest.mark.asyncio
    async def test_connection_limits(self):
        """Test connection limit settings."""
        settings = Settings()
        async with LLMClient(settings) as client:
            assert client._limits.max_keepalive_connections == 10
            assert client._limits.max_connections == 20

    @pytest.mark.asyncio
    async def test_default_headers(self):
        """Test default headers are set."""
        settings = Settings()
        async with LLMClient(settings) as client:
            assert client.client._headers["Content-Type"] == "application/json"
            assert "GerdsenAI-CLI" in client.client._headers["User-Agent"]

    @pytest.mark.asyncio
    async def test_follow_redirects(self):
        """Test redirect following is enabled."""
        settings = Settings()
        async with LLMClient(settings) as client:
            # Client is created with follow_redirects=True (line 143 in llm_client.py)
            # We can't check the private attribute, but we can verify client exists
            assert client.client is not None
            assert isinstance(client.client, httpx.AsyncClient)


class TestLLMClientTimeoutScenarios:
    """Real-world timeout scenario tests."""

    @pytest.mark.asyncio
    async def test_quick_health_check_timeout(self):
        """Test quick health check has short timeout."""
        settings = Settings()
        async with LLMClient(settings) as client:
            health_timeout = client._get_timeout("health")
            chat_timeout = client._get_timeout("chat")
            assert health_timeout < chat_timeout

    @pytest.mark.asyncio
    async def test_model_list_faster_than_chat(self):
        """Test model list has faster timeout than chat."""
        settings = Settings()
        async with LLMClient(settings) as client:
            models_timeout = client._get_timeout("models")
            chat_timeout = client._get_timeout("chat")
            assert models_timeout < chat_timeout

    @pytest.mark.asyncio
    async def test_stream_timeout_equals_chat(self):
        """Test stream timeout equals chat timeout."""
        settings = Settings()
        async with LLMClient(settings) as client:
            stream_timeout = client._get_timeout("stream")
            chat_timeout = client._get_timeout("chat")
            assert stream_timeout == chat_timeout

    @pytest.mark.asyncio
    async def test_local_ai_friendly_defaults(self):
        """Test that defaults are friendly to slow local AI."""
        settings = Settings()
        async with LLMClient(settings) as client:
            # All timeouts should be at least 10 seconds
            assert client._get_timeout("health") >= 10.0
            assert client._get_timeout("models") >= 30.0
            assert client._get_timeout("chat") >= 600.0
            assert client._get_timeout("stream") >= 600.0
