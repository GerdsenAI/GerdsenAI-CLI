"""
Comprehensive tests for provider system.

Tests provider detection, model listing, chat completion, streaming,
error handling, and edge cases.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from gerdsenai_cli.core.providers import (
    HuggingFaceProvider,
    LMStudioProvider,
    OllamaProvider,
    ProviderDetector,
    ProviderType,
    VLLMProvider,
)


class TestOllamaProvider:
    """Test Ollama provider implementation."""

    @pytest.mark.asyncio
    async def test_detect_success(self):
        """Test successful Ollama detection."""
        provider = OllamaProvider("http://localhost:11434")

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": []}

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await provider.detect()
            assert result is True

    @pytest.mark.asyncio
    async def test_detect_failure(self):
        """Test Ollama detection failure."""
        provider = OllamaProvider("http://localhost:11434")

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )

            result = await provider.detect()
            assert result is False

    @pytest.mark.asyncio
    async def test_list_models(self):
        """Test listing Ollama models."""
        provider = OllamaProvider("http://localhost:11434")

        mock_response = {
            "models": [
                {
                    "name": "llama2:7b-q4_0",
                    "size": 4000000000,
                    "details": {
                        "context_length": 4096,
                        "family": "llama",
                        "parameter_size": "7B",
                        "quantization_level": "Q4_0",
                    },
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_http_response = MagicMock()
            mock_http_response.status_code = 200
            mock_http_response.json.return_value = mock_response
            mock_http_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_http_response
            )

            models = await provider.list_models()

            assert len(models) == 1
            assert models[0].name == "llama2:7b-q4_0"
            assert models[0].provider == ProviderType.OLLAMA
            assert models[0].size == 4000000000
            assert models[0].context_length == 4096
            assert models[0].quantization == "Q4_0"

    @pytest.mark.asyncio
    async def test_chat_completion(self):
        """Test Ollama chat completion."""
        provider = OllamaProvider("http://localhost:11434")

        messages = [{"role": "user", "content": "Hello!"}]

        mock_response = {"message": {"content": "Hi there!"}}

        with patch("httpx.AsyncClient") as mock_client:
            mock_http_response = MagicMock()
            mock_http_response.status_code = 200
            mock_http_response.json.return_value = mock_response
            mock_http_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_http_response
            )

            response = await provider.chat_completion(messages, model="llama2")

            assert response == "Hi there!"

    @pytest.mark.asyncio
    async def test_stream_completion(self):
        """Test Ollama streaming."""
        provider = OllamaProvider("http://localhost:11434")

        messages = [{"role": "user", "content": "Hello!"}]

        # Mock streaming response
        mock_lines = [
            b'{"message": {"content": "Hi "}}\n',
            b'{"message": {"content": "there!"}}\n',
        ]

        with patch("httpx.AsyncClient") as mock_client:
            mock_stream = MagicMock()

            # Make aiter_lines an async generator
            async def mock_aiter_lines():
                for line in mock_lines:
                    yield line.decode()

            mock_stream.aiter_lines = mock_aiter_lines
            mock_stream.raise_for_status = MagicMock()
            mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
            mock_stream.__aexit__ = AsyncMock(return_value=None)

            mock_client.return_value.__aenter__.return_value.stream = MagicMock(
                return_value=mock_stream
            )

            chunks = []
            async for chunk in provider.stream_completion(messages, model="llama2"):
                chunks.append(chunk)

            assert chunks == ["Hi ", "there!"]

    @pytest.mark.asyncio
    async def test_quantization_extraction(self):
        """Test GGUF quantization extraction."""
        provider = OllamaProvider()

        assert provider._extract_quantization("llama2:7b-q4_0") == "Q4_0"
        assert provider._extract_quantization("mistral:7b-q5_k_m") == "Q5_K_M"
        assert provider._extract_quantization("llama2:latest") is None

    def test_capabilities(self):
        """Test Ollama capabilities."""
        provider = OllamaProvider()
        caps = provider.get_capabilities()

        assert caps.supports_streaming is True
        assert caps.supports_json_mode is True
        assert caps.supports_vision is True
        assert caps.custom_capabilities["model_pull"] is True


class TestVLLMProvider:
    """Test vLLM provider implementation."""

    @pytest.mark.asyncio
    async def test_detect_success(self):
        """Test vLLM detection."""
        provider = VLLMProvider("http://localhost:8000")

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": []}

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await provider.detect()
            assert result is True

    @pytest.mark.asyncio
    async def test_stream_completion_openai_format(self):
        """Test vLLM streaming with OpenAI SSE format."""
        provider = VLLMProvider("http://localhost:8000")

        messages = [{"role": "user", "content": "Hello!"}]

        # Mock SSE streaming
        mock_lines = [
            "data: " + '{"choices": [{"delta": {"content": "Hi "}}]}',
            "data: " + '{"choices": [{"delta": {"content": "there!"}}]}',
            "data: [DONE]",
        ]

        with patch("httpx.AsyncClient") as mock_client:
            mock_stream = MagicMock()

            # Make aiter_lines an async generator
            async def mock_aiter_lines():
                for line in mock_lines:
                    yield line

            mock_stream.aiter_lines = mock_aiter_lines
            mock_stream.raise_for_status = MagicMock()
            mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
            mock_stream.__aexit__ = AsyncMock(return_value=None)

            mock_client.return_value.__aenter__.return_value.stream = MagicMock(
                return_value=mock_stream
            )

            chunks = []
            async for chunk in provider.stream_completion(messages, model="test"):
                chunks.append(chunk)

            assert chunks == ["Hi ", "there!"]

    def test_capabilities(self):
        """Test vLLM capabilities."""
        provider = VLLMProvider()
        caps = provider.get_capabilities()

        assert caps.supports_streaming is True
        assert caps.supports_grammar is True
        assert caps.max_batch_size == 32
        assert caps.custom_capabilities["continuous_batching"] is True


class TestLMStudioProvider:
    """Test LM Studio provider implementation."""

    @pytest.mark.asyncio
    async def test_list_models(self):
        """Test LM Studio model listing."""
        provider = LMStudioProvider("http://localhost:1234")

        mock_response = {
            "object": "list",
            "data": [
                {
                    "id": "llama-2-7b-chat.Q4_K_M.gguf",
                    "owned_by": "lm-studio",
                    "created": 1234567890,
                }
            ],
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_http_response = MagicMock()
            mock_http_response.status_code = 200
            mock_http_response.json.return_value = mock_response
            mock_http_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_http_response
            )

            models = await provider.list_models()

            assert len(models) == 1
            assert models[0].name == "llama-2-7b-chat.Q4_K_M.gguf"
            assert models[0].quantization == "Q4_K_M"

    @pytest.mark.asyncio
    async def test_quantization_extraction(self):
        """Test GGUF quantization pattern matching."""
        provider = LMStudioProvider()

        assert provider._extract_quantization("model.Q4_K_M.gguf") == "Q4_K_M"
        assert provider._extract_quantization("model.Q5_K_S.gguf") == "Q5_K_S"
        assert provider._extract_quantization("model.q4_0.gguf") == "Q4_0"


class TestHuggingFaceProvider:
    """Test Hugging Face TGI provider."""

    @pytest.mark.asyncio
    async def test_detect_with_info_endpoint(self):
        """Test HF TGI detection via /info endpoint."""
        provider = HuggingFaceProvider("http://localhost:8080")

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "model_id": "meta-llama/Llama-2-7b-chat-hf",
                "model_dtype": "float16",
            }

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await provider.detect()
            assert result is True

    @pytest.mark.asyncio
    async def test_messages_to_prompt_conversion(self):
        """Test message to prompt conversion."""
        provider = HuggingFaceProvider()

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        prompt = provider._messages_to_prompt(messages)

        assert "System: You are helpful." in prompt
        assert "User: Hello!" in prompt
        assert "Assistant: Hi there!" in prompt
        assert "User: How are you?" in prompt
        assert prompt.endswith("Assistant:")


class TestProviderDetector:
    """Test provider auto-detection system."""

    @pytest.mark.asyncio
    async def test_detect_ollama(self):
        """Test detecting Ollama provider."""
        detector = ProviderDetector()

        with patch("httpx.AsyncClient") as mock_client:
            # Ollama detection succeeds
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": []}

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            provider = await detector.detect_provider("http://localhost:11434")

            assert provider is not None
            assert isinstance(provider, OllamaProvider)
            assert provider.get_provider_type() == ProviderType.OLLAMA

    @pytest.mark.asyncio
    async def test_scan_common_ports(self):
        """Test scanning common ports."""
        detector = ProviderDetector()

        with patch.object(detector, "detect_provider") as mock_detect:
            # Mock Ollama found on 11434
            mock_detect.side_effect = lambda url, timeout: (
                OllamaProvider(url) if "11434" in url else None
            )

            providers = await detector.scan_common_ports(timeout=0.1)

            # Should find at least one provider
            assert len(providers) >= 1

            # Check if found Ollama
            ollama_found = any(
                isinstance(p, OllamaProvider) for url, p in providers if p
            )
            assert ollama_found

    @pytest.mark.asyncio
    async def test_auto_configure(self):
        """Test automatic configuration."""
        detector = ProviderDetector()

        with patch.object(detector, "get_best_provider") as mock_best:
            mock_provider = OllamaProvider("http://localhost:11434")
            mock_best.return_value = mock_provider

            config = await detector.auto_configure()

            assert config is not None
            assert config["protocol"] == "http"
            assert config["llm_host"] == "localhost"
            assert config["llm_port"] == "11434"

    def test_recommended_config(self):
        """Test recommended configurations."""
        detector = ProviderDetector()

        ollama_config = detector.get_recommended_config(ProviderType.OLLAMA)
        assert ollama_config["llm_port"] == "11434"

        lm_studio_config = detector.get_recommended_config(ProviderType.LM_STUDIO)
        assert lm_studio_config["llm_port"] == "1234"

        vllm_config = detector.get_recommended_config(ProviderType.VLLM)
        assert vllm_config["llm_port"] == "8000"


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_empty_model_list(self):
        """Test handling empty model list."""
        provider = OllamaProvider()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": []}
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            models = await provider.list_models()
            assert models == []

    @pytest.mark.asyncio
    async def test_malformed_response(self):
        """Test handling malformed JSON response."""
        provider = OllamaProvider()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            models = await provider.list_models()
            assert models == []  # Should return empty list, not crash

    @pytest.mark.asyncio
    async def test_network_timeout(self):
        """Test network timeout handling."""
        provider = OllamaProvider(timeout=0.001)  # Very short timeout

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )

            with pytest.raises(httpx.TimeoutException):
                await provider.chat_completion(
                    [{"role": "user", "content": "test"}], model="test"
                )

    @pytest.mark.asyncio
    async def test_connection_refused(self):
        """Test connection refused error."""
        provider = OllamaProvider("http://localhost:99999")  # Invalid port

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )

            result = await provider.detect()
            assert result is False

    @pytest.mark.asyncio
    async def test_http_error_handling(self):
        """Test HTTP error status codes."""
        provider = OllamaProvider()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not found", request=None, response=mock_response
            )

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(httpx.HTTPStatusError):
                await provider.chat_completion(
                    [{"role": "user", "content": "test"}], model="nonexistent"
                )

    @pytest.mark.asyncio
    async def test_streaming_connection_loss(self):
        """Test handling connection loss during streaming."""
        provider = OllamaProvider()

        messages = [{"role": "user", "content": "Hello!"}]

        # Mock partial stream then disconnect
        async def mock_aiter_lines():
            yield '{"message": {"content": "Hi "}}'
            raise httpx.NetworkError("Connection lost")

        with patch("httpx.AsyncClient") as mock_client:
            mock_stream = MagicMock()
            mock_stream.aiter_lines = mock_aiter_lines
            mock_stream.raise_for_status = MagicMock()
            mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
            mock_stream.__aexit__ = AsyncMock(return_value=None)

            mock_client.return_value.__aenter__.return_value.stream = MagicMock(
                return_value=mock_stream
            )

            chunks = []
            with pytest.raises(httpx.NetworkError):
                async for chunk in provider.stream_completion(messages, model="test"):
                    chunks.append(chunk)

            # Should have received the first chunk
            assert len(chunks) == 1
            assert chunks[0] == "Hi "


class TestIntegration:
    """Integration tests for provider system."""

    @pytest.mark.asyncio
    async def test_full_detection_flow(self):
        """Test complete provider detection and usage flow."""
        detector = ProviderDetector()

        # Mock multiple providers
        with patch("httpx.AsyncClient") as mock_client:

            def mock_get(url, **kwargs):
                response = MagicMock()
                if "/api/tags" in url:  # Ollama
                    response.status_code = 200
                    response.json.return_value = {"models": []}
                elif "/v1/models" in url:  # vLLM/LM Studio
                    response.status_code = 200
                    response.json.return_value = {"data": []}
                else:
                    response.status_code = 404
                return response

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=mock_get
            )

            # Detect provider
            provider = await detector.detect_provider("http://localhost:11434")
            assert provider is not None

            # Get capabilities
            caps = provider.get_capabilities()
            assert caps is not None
            assert caps.supports_streaming is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
