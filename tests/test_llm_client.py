"""
Tests for LLM client module.

Covers connection handling, retry logic, timeout configuration,
and response processing with proper mocking.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import RequestError, TimeoutException

from gerdsenai_cli.core.llm_client import LLMClient, LLMResponse, LLMError


class TestLLMClient:
    """Test suite for LLM client functionality."""
    
    def setup_method(self):
        """Set up test client instance."""
        self.client = LLMClient()
    
    def teardown_method(self):
        """Clean up after tests."""
        if hasattr(self.client, '_http_client') and self.client._http_client:
            asyncio.create_task(self.client._http_client.aclose())
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test client initialization with default settings."""
        assert self.client.base_url == "http://localhost:11434"
        assert self.client.timeout == 30.0
        assert self.client.max_retries == 3
        assert not self.client._http_client
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await self.client.health_check()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check failure handling."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = RequestError("Connection failed")
            
            result = await self.client.health_check()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_models_success(self):
        """Test successful model listing."""
        mock_models = {
            "models": [
                {"name": "llama2:7b", "size": 3825819519},
                {"name": "codellama:13b", "size": 7365960935}
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_models
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            models = await self.client.get_models()
            assert len(models) == 2
            assert "llama2:7b" in models
            assert "codellama:13b" in models
    
    @pytest.mark.asyncio
    async def test_chat_completion_success(self):
        """Test successful chat completion."""
        mock_response_data = {
            "message": {
                "role": "assistant",
                "content": "Hello! How can I help you today?"
            },
            "done": True
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            response = await self.client.chat_completion(
                model="llama2:7b",
                messages=[{"role": "user", "content": "Hello"}]
            )
            
            assert isinstance(response, LLMResponse)
            assert response.content == "Hello! How can I help you today?"
            assert response.model == "llama2:7b"
            assert response.usage is not None
    
    @pytest.mark.asyncio
    async def test_retry_logic(self):
        """Test retry logic on failures."""
        with patch('httpx.AsyncClient') as mock_client:
            # First two calls fail, third succeeds
            mock_client.return_value.__aenter__.return_value.post.side_effect = [
                RequestError("Connection failed"),
                TimeoutException("Request timeout"),
                MagicMock(
                    status_code=200,
                    json=lambda: {
                        "message": {"role": "assistant", "content": "Success"},
                        "done": True
                    }
                )
            ]
            
            response = await self.client.chat_completion(
                model="llama2:7b",
                messages=[{"role": "user", "content": "Test retry"}]
            )
            
            assert response.content == "Success"
            # Should have made 3 attempts (2 failures + 1 success)
            assert mock_client.return_value.__aenter__.return_value.post.call_count == 3
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test behavior when max retries are exceeded."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = RequestError("Persistent failure")
            
            with pytest.raises(LLMError):
                await self.client.chat_completion(
                    model="llama2:7b",
                    messages=[{"role": "user", "content": "Test failure"}]
                )
    
    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """Test streaming chat completion."""
        mock_chunks = [
            b'{"message": {"content": "Hello"}, "done": false}\n',
            b'{"message": {"content": " there"}, "done": false}\n', 
            b'{"message": {"content": "!"}, "done": true}\n'
        ]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.aiter_lines.return_value = mock_chunks
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            content_parts = []
            async for chunk in self.client.chat_completion_stream(
                model="llama2:7b",
                messages=[{"role": "user", "content": "Hello"}]
            ):
                content_parts.append(chunk)
            
            assert len(content_parts) == 3
            assert "".join(content_parts) == "Hello there!"
    
    @pytest.mark.asyncio
    async def test_timeout_configuration(self):
        """Test that timeouts are properly configured."""
        client = LLMClient(timeout=10.0)
        assert client.timeout == 10.0
        
        # Test that timeout is applied in requests
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = TimeoutException("Timeout")
            
            with pytest.raises(LLMError):
                await client.health_check()
    
    def test_response_validation(self):
        """Test LLMResponse validation."""
        # Valid response
        response = LLMResponse(
            content="Test response",
            model="llama2:7b",
            role="assistant"
        )
        assert response.content == "Test response"
        assert response.model == "llama2:7b"
        
        # Test with usage info
        response_with_usage = LLMResponse(
            content="Test",
            model="llama2:7b", 
            role="assistant",
            usage={"prompt_tokens": 10, "completion_tokens": 5}
        )
        assert response_with_usage.usage["prompt_tokens"] == 10
