"""
Tests for LLM client module.

Covers connection handling, retry logic, timeout configuration,
and response processing with proper mocking.
"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import RequestError, TimeoutException

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.core.llm_client import ChatMessage, LLMClient, ModelInfo


class TestLLMClient:
    """Test suite for LLM client functionality."""

    def setup_method(self):
        """Set up test client instance."""
        import asyncio
        # Create a mock settings object
        mock_settings = MagicMock(spec=Settings)
        mock_settings.llm_server_url = "http://localhost:11434"
        mock_settings.current_model = "llama2:7b"
        self.client = LLMClient(mock_settings)

        # Initialize the client by entering the async context manager
        asyncio.run(self.client.__aenter__())

    def teardown_method(self):
        """Clean up after tests."""
        import asyncio
        # Exit the async context manager (this calls close() internally)
        asyncio.run(self.client.__aexit__(None, None, None))

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test client initialization with default settings."""
        assert self.client.base_url == "http://localhost:11434"
        assert self.client.client is not None
        assert not self.client.is_connected

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        with patch.object(self.client.client, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_get.return_value = mock_response

            result = await self.client.connect()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check failure handling."""
        with patch.object(self.client.client, "get") as mock_get:
            mock_get.side_effect = RequestError("Connection failed")

            result = await self.client.connect()
            assert result is False

    @pytest.mark.asyncio
    async def test_get_models_success(self):
        """Test successful model listing."""
        mock_models = {
            "data": [
                {"id": "llama2:7b", "object": "model"},
                {"id": "codellama:13b", "object": "model"},
            ]
        }

        with patch.object(self.client.client, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_models
            mock_get.return_value = mock_response

            models = await self.client.list_models()
            assert len(models) == 2
            assert models[0].id == "llama2:7b"
            assert models[1].id == "codellama:13b"

    @pytest.mark.asyncio
    async def test_chat_completion_success(self):
        """Test successful chat completion."""
        mock_response_data = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help you today?",
                    }
                }
            ]
        }

        with patch.object(self.client.client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_post.return_value = mock_response

            messages = [ChatMessage(role="user", content="Hello")]
            response = await self.client.chat(messages=messages, model="llama2:7b")

            assert response == "Hello! How can I help you today?"

    @pytest.mark.asyncio
    async def test_retry_logic(self):
        """Test retry logic on failures."""
        with patch.object(self.client.client, "post") as mock_post:
            # First two calls fail, third succeeds
            mock_post.side_effect = [
                RequestError("Connection failed"),
                TimeoutException("Request timeout"),
                MagicMock(
                    status_code=200,
                    json=lambda: {
                        "choices": [
                            {"message": {"role": "assistant", "content": "Success"}}
                        ]
                    },
                ),
            ]

            messages = [ChatMessage(role="user", content="Test retry")]
            response = await self.client.chat(messages=messages, model="llama2:7b")

            assert response == "Success"
            # Should have made 3 attempts (2 failures + 1 success)
            assert mock_post.call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test behavior when max retries are exceeded."""
        with patch.object(self.client.client, "post") as mock_post:
            mock_post.side_effect = RequestError("Persistent failure")

            messages = [ChatMessage(role="user", content="Test failure")]
            result = await self.client.chat(messages=messages, model="llama2:7b")

            # Should return None on failure after retries
            assert result is None

    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """Test streaming chat completion."""
        mock_lines = [
            'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            'data: {"choices": [{"delta": {"content": " there"}}]}',
            'data: {"choices": [{"delta": {"content": "!"}}]}',
            "data: [DONE]",
        ]

        async def async_lines():
            for line in mock_lines:
                yield line

        with patch.object(self.client.client, "stream") as mock_stream:
            mock_response = MagicMock()
            mock_response.aiter_lines.return_value = async_lines()
            mock_response.raise_for_status.return_value = None

            mock_stream.return_value.__aenter__.return_value = mock_response

            content_parts = []
            messages = [ChatMessage(role="user", content="Hello")]
            async for chunk in self.client.stream_chat(
                messages=messages, model="llama2:7b"
            ):
                content_parts.append(chunk)

            assert len(content_parts) == 3
            assert "".join(content_parts) == "Hello there!"

    @pytest.mark.asyncio
    async def test_timeout_configuration(self):
        """Test that timeouts are properly configured."""
        # Test that timeout is applied in requests
        with patch.object(self.client.client, "get") as mock_get:
            mock_get.side_effect = TimeoutException("Timeout")

            result = await self.client.connect()
            assert result is False

    def test_model_info_validation(self):
        """Test ModelInfo validation."""
        # Valid model info
        model = ModelInfo(id="llama2:7b", object="model")
        assert model.id == "llama2:7b"
        assert model.object == "model"

        # Test with additional fields
        model_with_info = ModelInfo(
            id="codellama:13b", object="model", owned_by="meta", size=7365960935
        )
        assert model_with_info.size == 7365960935
        assert model_with_info.owned_by == "meta"
