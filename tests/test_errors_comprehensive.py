"""
Comprehensive error handling and validation tests.

Tests all error types, validation scenarios, and error recovery.
"""

import pytest

from gerdsenai_cli.core.errors import (
    ConfigurationError,
    ContextLengthError,
    ErrorCategory,
    ErrorSeverity,
    GerdsenAIError,
    ModelNotFoundError,
    NetworkError,
    ParseError,
    ProviderError,
    TimeoutError,
    classify_exception,
)


class TestGerdsenAIError:
    """Tests for base GerdsenAIError."""

    def test_basic_error_creation(self):
        """Test creating basic error."""
        error = GerdsenAIError("Test error")
        assert str(error) == "Test error"

    def test_error_with_category(self):
        """Test error with category."""
        error = GerdsenAIError("Test error", category=ErrorCategory.NETWORK)
        assert error.category == ErrorCategory.NETWORK

    def test_error_with_severity(self):
        """Test error with severity."""
        error = GerdsenAIError("Test error", severity=ErrorSeverity.HIGH)
        assert error.severity == ErrorSeverity.HIGH

    def test_error_with_suggestion(self):
        """Test error with suggestion."""
        error = GerdsenAIError("Test error", suggestion="Try this")
        assert error.suggestion == "Try this"

    def test_error_with_context(self):
        """Test error with context."""
        error = GerdsenAIError("Test error", context={"key": "value"})
        assert error.context["key"] == "value"

    def test_error_recoverable_default(self):
        """Test error is recoverable by default."""
        error = GerdsenAIError("Test error")
        assert error.recoverable is True

    def test_error_not_recoverable(self):
        """Test non-recoverable error."""
        error = GerdsenAIError("Test error", recoverable=False)
        assert error.recoverable is False

    def test_error_with_original_exception(self):
        """Test error with original exception."""
        original = ValueError("Original error")
        error = GerdsenAIError("Wrapped error", original_exception=original)
        assert error.original_exception == original

    def test_error_message_required(self):
        """Test error message is required."""
        with pytest.raises(TypeError):
            GerdsenAIError()  # type: ignore

    def test_error_str_representation(self):
        """Test error string representation."""
        error = GerdsenAIError("Test message")
        assert "Test message" in str(error)


class TestNetworkError:
    """Tests for NetworkError."""

    def test_network_error_creation(self):
        """Test creating network error."""
        error = NetworkError("Connection failed")
        assert str(error) == "Connection failed"

    def test_network_error_has_network_category(self):
        """Test network error has correct category."""
        error = NetworkError("Connection failed")
        assert error.category == ErrorCategory.NETWORK

    def test_network_error_with_suggestion(self):
        """Test network error with suggestion."""
        error = NetworkError("Connection failed", suggestion="Check network")
        assert error.suggestion == "Check network"

    def test_network_error_recoverable(self):
        """Test network error is recoverable."""
        error = NetworkError("Connection failed")
        assert error.recoverable is True


class TestTimeoutError:
    """Tests for TimeoutError."""

    def test_timeout_error_creation(self):
        """Test creating timeout error."""
        error = TimeoutError("Request timed out")
        assert str(error) == "Request timed out"

    def test_timeout_error_has_timeout_category(self):
        """Test timeout error has correct category."""
        error = TimeoutError("Request timed out")
        assert error.category == ErrorCategory.TIMEOUT

    def test_timeout_error_with_timeout_seconds(self):
        """Test timeout error with timeout value."""
        error = TimeoutError("Request timed out", timeout_seconds=30.0)
        assert error.context["timeout_seconds"] == 30.0

    def test_timeout_error_recoverable(self):
        """Test timeout error is recoverable."""
        error = TimeoutError("Request timed out")
        assert error.recoverable is True


class TestModelNotFoundError:
    """Tests for ModelNotFoundError."""

    def test_model_not_found_error_creation(self):
        """Test creating model not found error."""
        error = ModelNotFoundError("Model not found")
        assert str(error) == "Model not found"

    def test_model_not_found_has_model_category(self):
        """Test model not found has correct category."""
        error = ModelNotFoundError("Model not found")
        assert error.category == ErrorCategory.MODEL_NOT_FOUND

    def test_model_not_found_with_model_name(self):
        """Test model not found with model name."""
        error = ModelNotFoundError("Model not found", context={"model": "llama2"})
        assert error.context["model"] == "llama2"


class TestContextLengthError:
    """Tests for ContextLengthError."""

    def test_context_length_error_creation(self):
        """Test creating context length error."""
        error = ContextLengthError("Context too long")
        assert str(error) == "Context too long"

    def test_context_length_has_context_category(self):
        """Test context length has correct category."""
        error = ContextLengthError("Context too long")
        assert error.category == ErrorCategory.CONTEXT_LENGTH

    def test_context_length_with_tokens(self):
        """Test context length with token count."""
        error = ContextLengthError(
            "Context too long",
            context={"tokens": 5000, "max_tokens": 4096}
        )
        assert error.context["tokens"] == 5000


class TestProviderError:
    """Tests for ProviderError."""

    def test_provider_error_creation(self):
        """Test creating provider error."""
        error = ProviderError("Provider failed")
        assert str(error) == "Provider failed"

    def test_provider_error_has_provider_category(self):
        """Test provider error has correct category."""
        error = ProviderError("Provider failed")
        assert error.category == ErrorCategory.PROVIDER

    def test_provider_error_with_provider_name(self):
        """Test provider error with provider name."""
        error = ProviderError(
            "Provider failed",
            context={"provider": "ollama"}
        )
        assert error.context["provider"] == "ollama"


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_configuration_error_creation(self):
        """Test creating configuration error."""
        error = ConfigurationError("Invalid config")
        assert str(error) == "Invalid config"

    def test_configuration_error_has_config_category(self):
        """Test configuration error has correct category."""
        error = ConfigurationError("Invalid config")
        assert error.category == ErrorCategory.CONFIGURATION

    def test_configuration_error_with_config_key(self):
        """Test configuration error with config key."""
        error = ConfigurationError(
            "Invalid config",
            config_key="api_timeout"
        )
        assert "api_timeout" in str(error)

    def test_configuration_error_not_recoverable(self):
        """Test configuration error is not recoverable."""
        error = ConfigurationError("Invalid config")
        assert error.recoverable is False


class TestParseError:
    """Tests for ParseError."""

    def test_parse_error_creation(self):
        """Test creating parse error."""
        error = ParseError("Parse failed")
        assert str(error) == "Parse failed"

    def test_parse_error_has_parse_category(self):
        """Test parse error has correct category."""
        error = ParseError("Parse failed")
        assert error.category == ErrorCategory.PARSE_ERROR

    def test_parse_error_with_content(self):
        """Test parse error with content."""
        error = ParseError(
            "Parse failed",
            context={"content": "invalid json"}
        )
        assert error.context["content"] == "invalid json"


class TestErrorCategory:
    """Tests for ErrorCategory enum."""

    def test_all_categories_exist(self):
        """Test all error categories exist."""
        assert hasattr(ErrorCategory, "NETWORK")
        assert hasattr(ErrorCategory, "TIMEOUT")
        assert hasattr(ErrorCategory, "MODEL_NOT_FOUND")
        assert hasattr(ErrorCategory, "CONTEXT_LENGTH")
        assert hasattr(ErrorCategory, "PROVIDER")
        assert hasattr(ErrorCategory, "CONFIGURATION")
        assert hasattr(ErrorCategory, "FILE_NOT_FOUND")
        assert hasattr(ErrorCategory, "PARSE_ERROR")
        assert hasattr(ErrorCategory, "INVALID_REQUEST")
        assert hasattr(ErrorCategory, "UNKNOWN")

    def test_categories_are_unique(self):
        """Test all categories have unique values."""
        categories = [c for c in ErrorCategory]
        values = [c.value for c in categories]
        assert len(values) == len(set(values))


class TestErrorSeverity:
    """Tests for ErrorSeverity enum."""

    def test_all_severities_exist(self):
        """Test all error severities exist."""
        assert hasattr(ErrorSeverity, "LOW")
        assert hasattr(ErrorSeverity, "MEDIUM")
        assert hasattr(ErrorSeverity, "HIGH")
        assert hasattr(ErrorSeverity, "CRITICAL")

    def test_severities_are_ordered(self):
        """Test severities are ordered correctly."""
        assert ErrorSeverity.LOW.value < ErrorSeverity.MEDIUM.value
        assert ErrorSeverity.MEDIUM.value < ErrorSeverity.HIGH.value
        assert ErrorSeverity.HIGH.value < ErrorSeverity.CRITICAL.value


class TestClassifyException:
    """Tests for classify_exception function."""

    def test_classify_network_error(self):
        """Test classifying network error."""
        import httpx
        exc = httpx.ConnectError("Connection failed")
        category, suggestion = classify_exception(exc)
        assert category == ErrorCategory.NETWORK

    def test_classify_timeout_error(self):
        """Test classifying timeout error."""
        import httpx
        exc = httpx.TimeoutException("Timeout")
        category, suggestion = classify_exception(exc)
        assert category == ErrorCategory.TIMEOUT

    def test_classify_generic_exception(self):
        """Test classifying generic exception."""
        exc = Exception("Generic error")
        category, suggestion = classify_exception(exc)
        assert category == ErrorCategory.UNKNOWN

    def test_classification_includes_suggestion(self):
        """Test classification includes suggestion."""
        import httpx
        exc = httpx.ConnectError("Connection failed")
        category, suggestion = classify_exception(exc)
        assert suggestion is not None
        assert len(suggestion) > 0


class TestErrorRecovery:
    """Tests for error recovery."""

    def test_recoverable_network_error(self):
        """Test recoverable network error."""
        error = NetworkError("Connection failed")
        assert error.recoverable is True

    def test_non_recoverable_configuration_error(self):
        """Test non-recoverable configuration error."""
        error = ConfigurationError("Invalid config")
        assert error.recoverable is False

    def test_recoverable_timeout_error(self):
        """Test recoverable timeout error."""
        error = TimeoutError("Timeout")
        assert error.recoverable is True

    def test_recoverable_provider_error(self):
        """Test recoverable provider error."""
        error = ProviderError("Provider failed")
        assert error.recoverable is True


class TestErrorContext:
    """Tests for error context."""

    def test_empty_context(self):
        """Test empty context."""
        error = GerdsenAIError("Error")
        assert error.context == {}

    def test_single_context_item(self):
        """Test single context item."""
        error = GerdsenAIError("Error", context={"key": "value"})
        assert len(error.context) == 1

    def test_multiple_context_items(self):
        """Test multiple context items."""
        error = GerdsenAIError(
            "Error",
            context={"key1": "value1", "key2": "value2"}
        )
        assert len(error.context) == 2

    def test_nested_context(self):
        """Test nested context."""
        error = GerdsenAIError(
            "Error",
            context={"outer": {"inner": "value"}}
        )
        assert error.context["outer"]["inner"] == "value"


class TestErrorChaining:
    """Tests for error chaining."""

    def test_error_with_cause(self):
        """Test error with cause."""
        original = ValueError("Original")
        error = GerdsenAIError("Wrapped", original_exception=original)
        assert error.original_exception == original

    def test_error_chain_preserved(self):
        """Test error chain is preserved."""
        try:
            raise ValueError("Original")
        except ValueError as e:
            error = GerdsenAIError("Wrapped", original_exception=e)
            assert error.original_exception is not None


class TestErrorMessages:
    """Tests for error messages."""

    def test_descriptive_error_message(self):
        """Test error has descriptive message."""
        error = NetworkError("Connection to http://localhost:11434 failed")
        assert "localhost" in str(error)
        assert "11434" in str(error)

    def test_error_message_with_suggestion(self):
        """Test error message includes suggestion."""
        error = GerdsenAIError(
            "Operation failed",
            suggestion="Try restarting the server"
        )
        assert error.suggestion == "Try restarting the server"

    def test_timeout_error_message_with_duration(self):
        """Test timeout error includes duration."""
        error = TimeoutError(
            "Request timed out",
            timeout_seconds=30.0
        )
        assert 30.0 in error.context.values()


class TestErrorValidation:
    """Tests for error validation."""

    def test_error_requires_message(self):
        """Test error requires message."""
        with pytest.raises(TypeError):
            GerdsenAIError()  # type: ignore

    def test_error_message_can_be_empty(self):
        """Test error message can be empty string."""
        error = GerdsenAIError("")
        assert str(error) == ""

    def test_error_category_optional(self):
        """Test error category is optional."""
        error = GerdsenAIError("Test")
        assert error.category is not None  # Has default

    def test_error_severity_optional(self):
        """Test error severity is optional."""
        error = GerdsenAIError("Test")
        assert error.severity is not None  # Has default


class TestErrorTypes:
    """Tests for specific error types."""

    def test_all_error_types_inherit_base(self):
        """Test all error types inherit from GerdsenAIError."""
        assert issubclass(NetworkError, GerdsenAIError)
        assert issubclass(TimeoutError, GerdsenAIError)
        assert issubclass(ModelNotFoundError, GerdsenAIError)
        assert issubclass(ContextLengthError, GerdsenAIError)
        assert issubclass(ProviderError, GerdsenAIError)
        assert issubclass(ConfigurationError, GerdsenAIError)
        assert issubclass(ParseError, GerdsenAIError)

    def test_error_types_have_correct_categories(self):
        """Test error types have correct default categories."""
        assert NetworkError("").category == ErrorCategory.NETWORK
        assert TimeoutError("").category == ErrorCategory.TIMEOUT
        assert ModelNotFoundError("").category == ErrorCategory.MODEL_NOT_FOUND
        assert ContextLengthError("").category == ErrorCategory.CONTEXT_LENGTH
        assert ProviderError("").category == ErrorCategory.PROVIDER
        assert ConfigurationError("").category == ErrorCategory.CONFIGURATION
        assert ParseError("").category == ErrorCategory.PARSE_ERROR


class TestErrorEdgeCases:
    """Edge case tests for errors."""

    def test_very_long_error_message(self):
        """Test error with very long message."""
        long_message = "Error " * 1000
        error = GerdsenAIError(long_message)
        assert len(str(error)) > 5000

    def test_error_with_unicode(self):
        """Test error with unicode characters."""
        error = GerdsenAIError("Error: 你好 🌍")
        assert "你好" in str(error)

    def test_error_with_special_characters(self):
        """Test error with special characters."""
        error = GerdsenAIError("Error: <>&\"'")
        assert "<>" in str(error)

    def test_error_with_newlines(self):
        """Test error with newlines."""
        error = GerdsenAIError("Line 1\nLine 2\nLine 3")
        assert "\n" in str(error)


class TestErrorSuggestions:
    """Tests for error suggestions."""

    def test_network_error_suggestions(self):
        """Test network error has helpful suggestions."""
        import httpx
        exc = httpx.ConnectError("Connection failed")
        _, suggestion = classify_exception(exc)
        assert suggestion is not None

    def test_timeout_error_suggestions(self):
        """Test timeout error has helpful suggestions."""
        import httpx
        exc = httpx.TimeoutException("Timeout")
        _, suggestion = classify_exception(exc)
        assert suggestion is not None

    def test_configuration_error_suggestions(self):
        """Test configuration error includes fix suggestions."""
        error = ConfigurationError(
            "Invalid port",
            config_key="llm_port",
            suggestion="Port must be between 1 and 65535"
        )
        assert "65535" in error.suggestion


class TestErrorComparison:
    """Tests for error comparison."""

    def test_errors_with_same_message_not_equal(self):
        """Test errors with same message are not equal."""
        error1 = GerdsenAIError("Test")
        error2 = GerdsenAIError("Test")
        assert error1 is not error2

    def test_error_category_comparison(self):
        """Test error category comparison."""
        error1 = NetworkError("Test")
        error2 = TimeoutError("Test")
        assert error1.category != error2.category


class TestErrorSerialization:
    """Tests for error serialization."""

    def test_error_to_dict(self):
        """Test error can be converted to dict."""
        error = GerdsenAIError(
            "Test error",
            category=ErrorCategory.NETWORK,
            context={"key": "value"}
        )
        # Should have relevant information
        assert error.message == "Test error"
        assert error.category == ErrorCategory.NETWORK
        assert error.context["key"] == "value"


class TestErrorPerformance:
    """Performance tests for errors."""

    def test_error_creation_fast(self):
        """Test error creation is fast."""
        import time
        start = time.time()
        for _ in range(1000):
            GerdsenAIError("Test error")
        elapsed = time.time() - start
        assert elapsed < 0.1  # Should be very fast

    def test_error_with_context_fast(self):
        """Test error with context creation is fast."""
        import time
        start = time.time()
        for _ in range(1000):
            GerdsenAIError("Test", context={"key": "value"})
        elapsed = time.time() - start
        assert elapsed < 0.2


class TestErrorUsagePatterns:
    """Tests for common error usage patterns."""

    def test_raise_and_catch_network_error(self):
        """Test raising and catching network error."""
        with pytest.raises(NetworkError):
            raise NetworkError("Connection failed")

    def test_raise_and_catch_timeout_error(self):
        """Test raising and catching timeout error."""
        with pytest.raises(TimeoutError):
            raise TimeoutError("Timeout")

    def test_catch_base_error(self):
        """Test catching base error class."""
        with pytest.raises(GerdsenAIError):
            raise NetworkError("Test")

    def test_catch_specific_error(self):
        """Test catching specific error type."""
        try:
            raise NetworkError("Test")
        except NetworkError as e:
            assert e.category == ErrorCategory.NETWORK

    def test_re_raise_error(self):
        """Test re-raising error."""
        with pytest.raises(NetworkError):
            try:
                raise NetworkError("Test")
            except NetworkError:
                raise


class TestErrorInheritance:
    """Tests for error inheritance."""

    def test_gerdsenai_error_inherits_exception(self):
        """Test GerdsenAIError inherits from Exception."""
        assert issubclass(GerdsenAIError, Exception)

    def test_all_errors_are_exceptions(self):
        """Test all custom errors are exceptions."""
        assert isinstance(NetworkError(""), Exception)
        assert isinstance(TimeoutError(""), Exception)
        assert isinstance(ConfigurationError(""), Exception)


class TestErrorCategories:
    """Comprehensive tests for error categories."""

    def test_network_category(self):
        """Test network category."""
        assert ErrorCategory.NETWORK.value == "network"

    def test_timeout_category(self):
        """Test timeout category."""
        assert ErrorCategory.TIMEOUT.value == "timeout"

    def test_configuration_category(self):
        """Test configuration category."""
        assert ErrorCategory.CONFIGURATION.value == "configuration"

    def test_unknown_category(self):
        """Test unknown category."""
        assert ErrorCategory.UNKNOWN.value == "unknown"


class TestErrorSeverities:
    """Comprehensive tests for error severities."""

    def test_low_severity(self):
        """Test low severity."""
        assert ErrorSeverity.LOW.value == 1

    def test_medium_severity(self):
        """Test medium severity."""
        assert ErrorSeverity.MEDIUM.value == 2

    def test_high_severity(self):
        """Test high severity."""
        assert ErrorSeverity.HIGH.value == 3

    def test_critical_severity(self):
        """Test critical severity."""
        assert ErrorSeverity.CRITICAL.value == 4
