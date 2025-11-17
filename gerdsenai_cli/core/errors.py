"""
Comprehensive Error Handling System.

Defines error types, classification, and recovery strategies.
"""

from enum import Enum
from typing import Any, Optional


class ErrorCategory(Enum):
    """Categories of errors for handling strategies."""

    NETWORK = "network"  # Connection issues, DNS failures
    TIMEOUT = "timeout"  # Request timeout
    AUTH = "authentication"  # Authentication/authorization failures
    RATE_LIMIT = "rate_limit"  # Rate limiting
    MODEL_NOT_FOUND = "model_not_found"  # Model doesn't exist
    INVALID_REQUEST = "invalid_request"  # Malformed request
    CONTEXT_LENGTH = "context_length"  # Context window exceeded
    PROVIDER_ERROR = "provider_error"  # Provider-specific error
    FILE_NOT_FOUND = "file_not_found"  # File operation error
    PARSE_ERROR = "parse_error"  # Response parsing error
    CONFIGURATION = "configuration"  # Configuration error
    UNKNOWN = "unknown"  # Unknown error


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    LOW = "low"  # Minor issue, operation can continue
    MEDIUM = "medium"  # Significant issue, may need user intervention
    HIGH = "high"  # Critical issue, operation must stop
    CRITICAL = "critical"  # System-level failure


class GerdsenAIError(Exception):
    """
    Base error class with rich context.

    All custom errors should inherit from this.
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        recoverable: bool = True,
        suggestion: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize error with comprehensive context.

        Args:
            message: Human-readable error message
            category: Error category for handling
            severity: Severity level
            recoverable: Whether error can be recovered from
            suggestion: Suggestion for fixing the error
            context: Additional context dict
            original_exception: Original exception if wrapped
        """
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.recoverable = recoverable
        self.suggestion = suggestion
        self.context = context or {}
        self.original_exception = original_exception

    def to_dict(self) -> dict[str, Any]:
        """
        Convert error to dictionary for logging/serialization.

        Returns:
            Error information as dict
        """
        return {
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "suggestion": self.suggestion,
            "context": self.context,
            "original_error": str(self.original_exception) if self.original_exception else None
        }

    def __str__(self) -> str:
        """String representation with suggestion."""
        parts = [f"[{self.category.value.upper()}] {self.message}"]

        if self.suggestion:
            parts.append(f"💡 Suggestion: {self.suggestion}")

        if self.context:
            parts.append(f"Context: {self.context}")

        return "\n".join(parts)


# Specific error classes

class NetworkError(GerdsenAIError):
    """Network-related error."""

    def __init__(
        self,
        message: str,
        suggestion: Optional[str] = None,
        context: Optional[dict] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            suggestion=suggestion or "Check your network connection and try again",
            context=context,
            original_exception=original_exception
        )


class TimeoutError(GerdsenAIError):
    """Request timeout error."""

    def __init__(
        self,
        message: str,
        timeout_seconds: float,
        suggestion: Optional[str] = None,
        context: Optional[dict] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.TIMEOUT,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            suggestion=suggestion or f"Request timed out after {timeout_seconds}s. Try increasing timeout or using a faster model.",
            context=context or {"timeout_seconds": timeout_seconds}
        )


class ModelNotFoundError(GerdsenAIError):
    """Model not available error."""

    def __init__(
        self,
        model_name: str,
        available_models: Optional[list[str]] = None,
        suggestion: Optional[str] = None
    ):
        super().__init__(
            message=f"Model '{model_name}' not found",
            category=ErrorCategory.MODEL_NOT_FOUND,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            suggestion=suggestion or self._generate_suggestion(available_models),
            context={"model_name": model_name, "available_models": available_models}
        )

    @staticmethod
    def _generate_suggestion(available_models: Optional[list[str]]) -> str:
        """Generate helpful suggestion based on available models."""
        if available_models:
            return f"Available models: {', '.join(available_models[:5])}. Use /models to list all models."
        return "Use /models to see available models, or pull a model first."


class ContextLengthError(GerdsenAIError):
    """Context window exceeded error."""

    def __init__(
        self,
        current_tokens: int,
        max_tokens: int,
        suggestion: Optional[str] = None
    ):
        super().__init__(
            message=f"Context length {current_tokens} exceeds maximum {max_tokens}",
            category=ErrorCategory.CONTEXT_LENGTH,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            suggestion=suggestion or "Try reducing context or using a model with larger context window",
            context={"current_tokens": current_tokens, "max_tokens": max_tokens}
        )


class ProviderError(GerdsenAIError):
    """Provider-specific error."""

    def __init__(
        self,
        provider_name: str,
        message: str,
        can_fallback: bool = False,
        suggestion: Optional[str] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(
            message=f"{provider_name}: {message}",
            category=ErrorCategory.PROVIDER_ERROR,
            severity=ErrorSeverity.MEDIUM if can_fallback else ErrorSeverity.HIGH,
            recoverable=can_fallback,
            suggestion=suggestion,
            context={"provider": provider_name, "can_fallback": can_fallback},
            original_exception=original_exception
        )
        self.can_fallback = can_fallback


class ConfigurationError(GerdsenAIError):
    """Configuration error."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        suggestion: Optional[str] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            suggestion=suggestion or "Check your configuration file or use /config to update settings",
            context={"config_key": config_key} if config_key else {}
        )


class ParseError(GerdsenAIError):
    """Response parsing error."""

    def __init__(
        self,
        message: str,
        raw_response: Optional[str] = None,
        suggestion: Optional[str] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.PARSE_ERROR,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            suggestion=suggestion or "The response format was unexpected. Trying alternative parsing.",
            context={"raw_response": raw_response[:500] if raw_response else None}
        )


def classify_exception(exception: Exception) -> tuple[ErrorCategory, str]:
    """
    Classify a raw exception into an error category.

    Args:
        exception: The exception to classify

    Returns:
        (category, suggestion) tuple
    """
    import httpx

    exception_type = type(exception).__name__
    error_message = str(exception).lower()

    # Network errors
    if isinstance(exception, (httpx.ConnectError, httpx.NetworkError, ConnectionError)):
        return (
            ErrorCategory.NETWORK,
            "Check that the LLM server is running and accessible"
        )

    # Timeout errors
    if isinstance(exception, (httpx.TimeoutException, asyncio.TimeoutError)):
        return (
            ErrorCategory.TIMEOUT,
            "Increase timeout or use a faster model"
        )

    # HTTP errors
    if isinstance(exception, httpx.HTTPStatusError):
        status_code = exception.response.status_code

        if status_code == 401 or status_code == 403:
            return (ErrorCategory.AUTH, "Check your API credentials")
        elif status_code == 404:
            return (ErrorCategory.MODEL_NOT_FOUND, "Model not found, check model name")
        elif status_code == 429:
            return (ErrorCategory.RATE_LIMIT, "Rate limit exceeded, wait before retrying")
        elif 500 <= status_code < 600:
            return (ErrorCategory.PROVIDER_ERROR, "Provider server error, try again later")

    # Context length errors
    if "context" in error_message and ("length" in error_message or "limit" in error_message):
        return (
            ErrorCategory.CONTEXT_LENGTH,
            "Reduce context size or use a model with larger context window"
        )

    # File errors
    if isinstance(exception, (FileNotFoundError, IsADirectoryError, PermissionError)):
        return (ErrorCategory.FILE_NOT_FOUND, "Check file path and permissions")

    # Parse errors
    if isinstance(exception, (ValueError, json.JSONDecodeError, KeyError)):
        return (ErrorCategory.PARSE_ERROR, "Response parsing failed, retrying with different format")

    # Unknown
    return (ErrorCategory.UNKNOWN, "An unexpected error occurred")


import json
import asyncio
