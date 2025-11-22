"""
Comprehensive tests for error handling and retry logic.

Tests error classification, retry strategies, circuit breaker,
and error recovery scenarios.
"""

import asyncio
from unittest.mock import MagicMock

import httpx
import pytest

from gerdsenai_cli.core.errors import (
    ContextLengthError,
    ErrorCategory,
    GerdsenAIError,
    ModelNotFoundError,
    NetworkError,
    ParseError,
    ProviderError,
    TimeoutError,
    classify_exception,
)
from gerdsenai_cli.core.retry import CircuitBreaker, RetryStrategy


class TestErrorClassification:
    """Test error classification system."""

    def test_network_error_creation(self):
        """Test NetworkError with rich context."""
        error = NetworkError(
            message="Connection failed",
            suggestion="Check network connection",
            context={"url": "http://localhost:11434"},
        )

        assert error.message == "Connection failed"
        assert error.category == ErrorCategory.NETWORK
        assert error.recoverable is True
        assert "Check network connection" in error.suggestion
        assert error.context["url"] == "http://localhost:11434"

    def test_timeout_error_creation(self):
        """Test TimeoutError with timeout context."""
        error = TimeoutError(message="Request timed out", timeout_seconds=30.0)

        assert error.category == ErrorCategory.TIMEOUT
        assert error.context["timeout_seconds"] == 30.0
        assert "30.0s" in error.suggestion

    def test_model_not_found_error_with_suggestions(self):
        """Test ModelNotFoundError with available models."""
        error = ModelNotFoundError(
            model_name="llama3:8b",
            available_models=["llama2:7b", "mistral:7b", "codellama:7b"],
        )

        assert error.category == ErrorCategory.MODEL_NOT_FOUND
        assert "llama3:8b" in error.message
        assert "llama2:7b" in error.suggestion
        assert "mistral:7b" in error.suggestion

    def test_context_length_error(self):
        """Test ContextLengthError."""
        error = ContextLengthError(current_tokens=10000, max_tokens=4096)

        assert error.category == ErrorCategory.CONTEXT_LENGTH
        assert error.context["current_tokens"] == 10000
        assert error.context["max_tokens"] == 4096
        assert error.recoverable is True

    def test_provider_error_with_fallback(self):
        """Test ProviderError with fallback capability."""
        error = ProviderError(
            provider_name="Ollama",
            message="Model loading failed",
            can_fallback=True,
        )

        assert error.category == ErrorCategory.PROVIDER_ERROR
        assert error.can_fallback is True
        assert error.recoverable is True

    def test_error_to_dict(self):
        """Test error serialization."""
        error = NetworkError(
            message="Connection lost",
            context={"attempt": 1},
            original_exception=ValueError("Test"),
        )

        error_dict = error.to_dict()

        assert error_dict["message"] == "Connection lost"
        assert error_dict["category"] == "network"
        assert error_dict["recoverable"] is True
        assert error_dict["context"]["attempt"] == 1
        assert "Test" in error_dict["original_error"]

    def test_error_string_representation(self):
        """Test error __str__ formatting."""
        error = ModelNotFoundError(
            model_name="test-model",
            available_models=["model1", "model2"],
        )

        error_str = str(error)

        assert "MODEL_NOT_FOUND" in error_str
        assert "test-model" in error_str
        assert "Suggestion:" in error_str


class TestExceptionClassification:
    """Test automatic exception classification."""

    def test_classify_httpx_connect_error(self):
        """Test classifying connection errors."""
        exc = httpx.ConnectError("Connection refused")
        category, suggestion = classify_exception(exc)

        assert category == ErrorCategory.NETWORK
        assert "running" in suggestion.lower()

    def test_classify_httpx_timeout(self):
        """Test classifying timeout errors."""
        exc = httpx.TimeoutException("Request timeout")
        category, suggestion = classify_exception(exc)

        assert category == ErrorCategory.TIMEOUT
        assert "timeout" in suggestion.lower()

    def test_classify_http_401(self):
        """Test classifying 401 authentication errors."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        exc = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        category, suggestion = classify_exception(exc)

        assert category == ErrorCategory.AUTH
        assert "credentials" in suggestion.lower()

    def test_classify_http_404(self):
        """Test classifying 404 not found errors."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        exc = httpx.HTTPStatusError(
            "Not found", request=MagicMock(), response=mock_response
        )

        category, suggestion = classify_exception(exc)

        assert category == ErrorCategory.MODEL_NOT_FOUND

    def test_classify_http_429(self):
        """Test classifying 429 rate limit errors."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        exc = httpx.HTTPStatusError(
            "Too many requests", request=MagicMock(), response=mock_response
        )

        category, suggestion = classify_exception(exc)

        assert category == ErrorCategory.RATE_LIMIT

    def test_classify_context_length_error(self):
        """Test classifying context length errors from message."""
        exc = ValueError("context length exceeded maximum limit")
        category, suggestion = classify_exception(exc)

        assert category == ErrorCategory.CONTEXT_LENGTH

    def test_classify_file_not_found(self):
        """Test classifying file errors."""
        exc = FileNotFoundError("File not found: test.py")
        category, suggestion = classify_exception(exc)

        assert category == ErrorCategory.FILE_NOT_FOUND

    def test_classify_json_decode_error(self):
        """Test classifying JSON parse errors."""
        import json

        exc = json.JSONDecodeError("Invalid JSON", "", 0)
        category, suggestion = classify_exception(exc)

        assert category == ErrorCategory.PARSE_ERROR


class TestRetryStrategy:
    """Test retry strategy with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_success_on_first_attempt(self):
        """Test operation succeeds on first try."""
        retry = RetryStrategy()
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry.execute_with_retry(operation, operation_name="test")

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """Test retry succeeds after transient failures."""
        retry = RetryStrategy()
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.NetworkError("Temporary network issue")
            return "success"

        result = await retry.execute_with_retry(
            operation, operation_name="test", category=ErrorCategory.NETWORK
        )

        assert result == "success"
        assert call_count == 3  # Failed twice, succeeded third time

    @pytest.mark.asyncio
    async def test_retry_exhaustion(self):
        """Test all retries exhausted."""
        retry = RetryStrategy(max_retries={ErrorCategory.NETWORK: 2})

        async def operation():
            raise httpx.NetworkError("Persistent failure")

        with pytest.raises(httpx.NetworkError):
            await retry.execute_with_retry(
                operation, operation_name="test", category=ErrorCategory.NETWORK
            )

    @pytest.mark.asyncio
    async def test_no_retry_for_unrecoverable(self):
        """Test no retry for unrecoverable errors."""
        retry = RetryStrategy()
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            # Context length error should not retry
            raise GerdsenAIError(
                message="Context too long",
                category=ErrorCategory.CONTEXT_LENGTH,
                recoverable=False,
            )

        with pytest.raises(GerdsenAIError):
            await retry.execute_with_retry(
                operation, operation_name="test", category=ErrorCategory.CONTEXT_LENGTH
            )

        assert call_count == 1  # No retries

    @pytest.mark.asyncio
    async def test_retry_with_callback(self):
        """Test retry callbacks are invoked."""
        retry = RetryStrategy()
        retry_calls = []

        def on_retry(attempt, exception):
            retry_calls.append((attempt, str(exception)))

        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise NetworkError("Test error")
            return "success"

        await retry.execute_with_retry(
            operation, operation_name="test", on_retry=on_retry
        )

        assert len(retry_calls) == 1
        assert retry_calls[0][0] == 1  # First retry

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test exponential backoff delays."""
        retry = RetryStrategy(
            backoff_factors={ErrorCategory.NETWORK: 2.0},
            initial_delay=0.1,
            jitter=False,
        )

        call_count = 0
        start_time = asyncio.get_event_loop().time()

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("Test")
            return "success"

        await retry.execute_with_retry(
            operation, operation_name="test", category=ErrorCategory.NETWORK
        )

        elapsed = asyncio.get_event_loop().time() - start_time

        # Should have delays: 0.1s + 0.2s = 0.3s minimum
        assert elapsed >= 0.3

    @pytest.mark.asyncio
    async def test_fallback_execution(self):
        """Test fallback operation when primary fails."""
        retry = RetryStrategy()

        async def primary():
            raise NetworkError("Primary failed")

        async def fallback():
            return "fallback_result"

        result = await retry.execute_with_fallback(
            primary, fallback, operation_name="test"
        )

        assert result == "fallback_result"

    @pytest.mark.asyncio
    async def test_timeout_enforcement(self):
        """Test operation timeout enforcement."""
        retry = RetryStrategy()

        async def slow_operation():
            await asyncio.sleep(10)  # Way too slow
            return "done"

        with pytest.raises(TimeoutError):
            await retry.execute_with_timeout(
                slow_operation, timeout_seconds=0.1, operation_name="test"
            )

    def test_should_retry_decision(self):
        """Test should_retry decision logic."""
        retry = RetryStrategy()

        # Recoverable error, should retry
        should, delay = retry.should_retry(NetworkError("Test"), attempt=1)
        assert should is True
        assert delay > 0

        # Unrecoverable error, should not retry
        config_error = GerdsenAIError(
            message="Bad config",
            category=ErrorCategory.CONFIGURATION,
            recoverable=False,
        )
        should, delay = retry.should_retry(config_error, attempt=1)
        assert should is False
        assert delay == 0

        # Too many attempts
        should, delay = retry.should_retry(NetworkError("Test"), attempt=10)
        assert should is False


class TestCircuitBreaker:
    """Test circuit breaker pattern."""

    @pytest.mark.asyncio
    async def test_circuit_closed_success(self):
        """Test circuit breaker with successful operations."""
        breaker = CircuitBreaker(failure_threshold=3)

        async def operation():
            return "success"

        result = await breaker.call(operation, operation_name="test")

        assert result == "success"
        assert breaker.state == "closed"
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self):
        """Test circuit opens after failure threshold."""
        breaker = CircuitBreaker(failure_threshold=3)

        async def failing_operation():
            raise Exception("Always fails")

        # Fail 3 times to hit threshold
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(failing_operation, operation_name="test")

        assert breaker.state == "open"
        assert breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_circuit_open_rejects_calls(self):
        """Test circuit breaker rejects calls when open."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=100.0)

        async def failing_operation():
            raise Exception("Fails")

        # Trigger circuit open
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_operation, operation_name="test")

        # Circuit should now be open and reject calls
        with pytest.raises(GerdsenAIError) as exc_info:
            await breaker.call(failing_operation, operation_name="test")

        assert "Circuit breaker is OPEN" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_circuit_half_open_recovery(self):
        """Test circuit enters half-open state after timeout."""

        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        async def initially_failing():
            if breaker.state == "half_open":
                return "recovered"
            raise Exception("Still failing")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(initially_failing, operation_name="test")

        assert breaker.state == "open"

        # Wait for recovery timeout
        await asyncio.sleep(0.2)

        # Next call should attempt recovery
        result = await breaker.call(initially_failing, operation_name="test")

        assert result == "recovered"
        assert breaker.state == "closed"
        assert breaker.failure_count == 0


class TestErrorRecovery:
    """Test error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_network_error_recovery(self):
        """Test automatic recovery from network errors."""
        retry = RetryStrategy()
        attempts = []

        async def flaky_network():
            attempts.append(len(attempts) + 1)
            if len(attempts) < 2:
                raise NetworkError("Connection lost")
            return "recovered"

        result = await retry.execute_with_retry(
            flaky_network, operation_name="network_test"
        )

        assert result == "recovered"
        assert len(attempts) == 2

    @pytest.mark.asyncio
    async def test_rate_limit_with_backoff(self):
        """Test rate limit handling with exponential backoff."""
        retry = RetryStrategy(
            backoff_factors={ErrorCategory.RATE_LIMIT: 2.0}, initial_delay=0.05
        )

        attempts = []

        async def rate_limited():
            attempts.append(len(attempts) + 1)
            if len(attempts) < 3:
                mock_response = MagicMock()
                mock_response.status_code = 429
                raise httpx.HTTPStatusError(
                    "Too many requests", request=MagicMock(), response=mock_response
                )
            return "success"

        result = await retry.execute_with_retry(
            rate_limited, operation_name="rate_limit_test"
        )

        assert result == "success"
        assert len(attempts) == 3

    @pytest.mark.asyncio
    async def test_parse_error_fallback(self):
        """Test parse error with fallback parsing."""
        retry = RetryStrategy()

        attempts = []

        async def parse_response():
            attempts.append(len(attempts) + 1)
            if len(attempts) == 1:
                raise ParseError("Invalid JSON")
            return "parsed successfully"

        result = await retry.execute_with_retry(
            parse_response, operation_name="parse_test", category=ErrorCategory.PARSE_ERROR
        )

        assert result == "parsed successfully"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
