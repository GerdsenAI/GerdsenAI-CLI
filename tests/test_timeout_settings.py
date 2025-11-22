"""
Tests for timeout configuration and settings.

Verifies that timeout settings are properly configured for local AI models.
"""

import pytest

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.constants import LLMDefaults
from gerdsenai_cli.core.llm_client import OPERATION_TIMEOUTS, LLMClient


class TestTimeoutConstants:
    """Tests for timeout constants."""

    def test_operation_timeouts_increased(self):
        """Test that operation timeouts are increased for local AI."""
        # Health check should be at least 10 seconds
        assert OPERATION_TIMEOUTS["health"] >= 10.0

        # Model listing should be at least 30 seconds
        assert OPERATION_TIMEOUTS["models"] >= 30.0

        # Chat should be at least 600 seconds (10 minutes)
        assert OPERATION_TIMEOUTS["chat"] >= 600.0

        # Stream should be at least 600 seconds
        assert OPERATION_TIMEOUTS["stream"] >= 600.0

        # Default should be at least 600 seconds
        assert OPERATION_TIMEOUTS["default"] >= 600.0

    def test_llm_defaults_timeout(self):
        """Test LLM defaults timeout constants."""
        # Intent detection should be at least 60 seconds
        assert LLMDefaults.INTENT_DETECTION_TIMEOUT_SECONDS >= 60.0

        # Default timeout should be at least 600 seconds
        assert LLMDefaults.DEFAULT_TIMEOUT_SECONDS >= 600.0

    def test_llm_defaults_max_tokens(self):
        """Test that max tokens is increased."""
        # Default max tokens should be at least 4096
        assert LLMDefaults.DEFAULT_MAX_TOKENS >= 4096


class TestSettingsTimeoutConfiguration:
    """Tests for Settings timeout configuration."""

    def test_default_timeouts(self):
        """Test default timeout values in Settings."""
        settings = Settings()

        # API timeout should be at least 600 seconds
        assert settings.api_timeout >= 600.0

        # Health check timeout
        assert settings.health_check_timeout >= 10.0

        # Model list timeout
        assert settings.model_list_timeout >= 30.0

        # Chat timeout
        assert settings.chat_timeout >= 600.0

        # Stream timeout
        assert settings.stream_timeout >= 600.0

    def test_custom_timeouts(self):
        """Test setting custom timeout values."""
        settings = Settings(
            api_timeout=1200.0,
            health_check_timeout=20.0,
            model_list_timeout=60.0,
            chat_timeout=1800.0,
            stream_timeout=1800.0,
        )

        assert settings.api_timeout == 1200.0
        assert settings.health_check_timeout == 20.0
        assert settings.model_list_timeout == 60.0
        assert settings.chat_timeout == 1800.0
        assert settings.stream_timeout == 1800.0

    def test_timeout_validation_min(self):
        """Test timeout minimum validation."""
        with pytest.raises(ValueError):
            Settings(api_timeout=0.5)  # Below minimum

        with pytest.raises(ValueError):
            Settings(health_check_timeout=0.0)

    def test_timeout_validation_max(self):
        """Test timeout maximum validation."""
        with pytest.raises(ValueError):
            Settings(api_timeout=4000.0)  # Above maximum (3600)

        # Should accept maximum
        settings = Settings(api_timeout=3600.0)
        assert settings.api_timeout == 3600.0

    def test_timeout_settings_persist(self):
        """Test that timeout settings can be serialized."""
        settings = Settings(
            api_timeout=1200.0,
            chat_timeout=1800.0,
        )

        # Convert to dict and back
        settings_dict = settings.model_dump()
        assert settings_dict["api_timeout"] == 1200.0
        assert settings_dict["chat_timeout"] == 1800.0

        # Reconstruct from dict
        new_settings = Settings(**settings_dict)
        assert new_settings.api_timeout == 1200.0
        assert new_settings.chat_timeout == 1800.0


class TestLLMClientTimeoutUsage:
    """Tests for LLMClient timeout usage."""

    @pytest.mark.asyncio
    async def test_llm_client_uses_settings_timeouts(self):
        """Test that LLMClient uses timeout settings."""
        settings = Settings(
            health_check_timeout=15.0,
            model_list_timeout=45.0,
            chat_timeout=900.0,
            stream_timeout=900.0,
        )

        async with LLMClient(settings) as client:
            # Check that client has access to settings
            assert client.settings.health_check_timeout == 15.0
            assert client.settings.model_list_timeout == 45.0
            assert client.settings.chat_timeout == 900.0
            assert client.settings.stream_timeout == 900.0

    @pytest.mark.asyncio
    async def test_llm_client_get_timeout_health(self):
        """Test _get_timeout for health operation."""
        settings = Settings(health_check_timeout=20.0)

        async with LLMClient(settings) as client:
            timeout = client._get_timeout("health")
            assert timeout == 20.0

    @pytest.mark.asyncio
    async def test_llm_client_get_timeout_models(self):
        """Test _get_timeout for models operation."""
        settings = Settings(model_list_timeout=60.0)

        async with LLMClient(settings) as client:
            timeout = client._get_timeout("models")
            assert timeout == 60.0

    @pytest.mark.asyncio
    async def test_llm_client_get_timeout_chat(self):
        """Test _get_timeout for chat operation."""
        settings = Settings(chat_timeout=1200.0)

        async with LLMClient(settings) as client:
            timeout = client._get_timeout("chat")
            assert timeout == 1200.0

    @pytest.mark.asyncio
    async def test_llm_client_get_timeout_stream(self):
        """Test _get_timeout for stream operation."""
        settings = Settings(stream_timeout=1500.0)

        async with LLMClient(settings) as client:
            timeout = client._get_timeout("stream")
            assert timeout == 1500.0

    @pytest.mark.asyncio
    async def test_llm_client_get_timeout_fallback(self):
        """Test _get_timeout fallback to api_timeout."""
        settings = Settings(api_timeout=800.0)

        async with LLMClient(settings) as client:
            # Unknown operation should fall back
            timeout = client._get_timeout("unknown_operation")
            assert timeout == 800.0

    @pytest.mark.asyncio
    async def test_llm_client_get_timeout_priority(self):
        """Test timeout priority: operation-specific > api_timeout > constant."""
        settings = Settings(
            api_timeout=600.0,
            chat_timeout=1200.0,
        )

        async with LLMClient(settings) as client:
            # Should use chat_timeout (operation-specific)
            chat_timeout = client._get_timeout("chat")
            assert chat_timeout == 1200.0

            # Should use api_timeout (fallback)
            unknown_timeout = client._get_timeout("unknown")
            assert unknown_timeout == 600.0


class TestTimeoutIntegration:
    """Integration tests for timeout configuration."""

    def test_all_timeouts_work_together(self):
        """Test that all timeout settings work together."""
        settings = Settings(
            api_timeout=1000.0,
            health_check_timeout=15.0,
            model_list_timeout=45.0,
            chat_timeout=1500.0,
            stream_timeout=1500.0,
        )

        # All should be set correctly
        assert settings.api_timeout == 1000.0
        assert settings.health_check_timeout == 15.0
        assert settings.model_list_timeout == 45.0
        assert settings.chat_timeout == 1500.0
        assert settings.stream_timeout == 1500.0

    def test_timeout_reasonable_for_local_ai(self):
        """Test that default timeouts are reasonable for local AI."""
        settings = Settings()

        # Should support slow local models
        assert settings.chat_timeout >= 300.0  # At least 5 minutes
        assert settings.stream_timeout >= 300.0

        # Should allow quick health checks
        assert settings.health_check_timeout <= 60.0  # No more than 1 minute

    @pytest.mark.asyncio
    async def test_timeout_configuration_end_to_end(self):
        """Test timeout configuration end-to-end."""
        # Create settings with custom timeouts
        settings = Settings(
            llm_server_url="http://localhost:11434",
            current_model="test-model",
            api_timeout=1200.0,
            health_check_timeout=20.0,
            chat_timeout=1800.0,
        )

        # Create client with settings
        async with LLMClient(settings) as client:
            # Verify all timeouts are accessible
            assert client._get_timeout("health") == 20.0
            assert client._get_timeout("chat") == 1800.0

            # Verify default timeout is set
            assert client._default_timeout == 1200.0


class TestTimeoutEdgeCases:
    """Edge case tests for timeout configuration."""

    def test_very_long_timeout(self):
        """Test with very long timeout (1 hour)."""
        settings = Settings(chat_timeout=3600.0)
        assert settings.chat_timeout == 3600.0

    def test_minimum_timeout(self):
        """Test with minimum timeout."""
        settings = Settings(health_check_timeout=1.0)
        assert settings.health_check_timeout == 1.0

    def test_timeout_float_precision(self):
        """Test timeout with float precision."""
        settings = Settings(chat_timeout=1234.567)
        assert settings.chat_timeout == pytest.approx(1234.567)

    def test_timeout_update_after_creation(self):
        """Test updating timeout after settings creation."""
        settings = Settings()
        original_timeout = settings.chat_timeout

        # Update timeout (if mutable)
        settings.chat_timeout = 2000.0
        assert settings.chat_timeout == 2000.0
        assert settings.chat_timeout != original_timeout


class TestTimeoutPerformance:
    """Performance tests for timeout configuration."""

    def test_timeout_lookup_performance(self):
        """Test that timeout lookup is fast."""
        settings = Settings()

        import time
        async def test_lookups():
            async with LLMClient(settings) as client:
                start = time.time()
                for _ in range(10000):
                    client._get_timeout("chat")
                    client._get_timeout("stream")
                    client._get_timeout("health")
                elapsed = time.time() - start

                # Should be very fast (< 0.1s for 30k lookups)
                assert elapsed < 0.5

        import asyncio
        asyncio.run(test_lookups())
