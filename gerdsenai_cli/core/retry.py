"""
Intelligent Retry Logic with Exponential Backoff.

Provides smart retry strategies for different error types.
"""

import asyncio
import logging
from typing import Any, Callable, Optional, TypeVar

from .errors import (
    ErrorCategory,
    GerdsenAIError,
    classify_exception,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryStrategy:
    """
    Intelligent retry with exponential backoff and jitter.

    Different error categories get different retry strategies.
    """

    # Default retry counts by error category
    DEFAULT_RETRIES = {
        ErrorCategory.NETWORK: 3,  # Network issues are often transient
        ErrorCategory.TIMEOUT: 2,  # Try again with increased patience
        ErrorCategory.RATE_LIMIT: 5,  # Rate limits require backoff
        ErrorCategory.PROVIDER_ERROR: 2,  # Provider issues may recover
        ErrorCategory.PARSE_ERROR: 1,  # Try once more with alternative parsing
        ErrorCategory.CONTEXT_LENGTH: 0,  # Can't fix by retrying
        ErrorCategory.MODEL_NOT_FOUND: 0,  # Won't fix itself
        ErrorCategory.AUTH: 0,  # Need user intervention
        ErrorCategory.FILE_NOT_FOUND: 0,  # Won't fix itself
        ErrorCategory.CONFIGURATION: 0,  # Need user fix
        ErrorCategory.INVALID_REQUEST: 0,  # Don't retry invalid requests
        ErrorCategory.UNKNOWN: 1,  # Give it one more try
    }

    # Backoff multipliers by category
    BACKOFF_MULTIPLIERS = {
        ErrorCategory.NETWORK: 2.0,  # Network: 1s, 2s, 4s
        ErrorCategory.TIMEOUT: 1.5,  # Timeout: 1s, 1.5s, 2.25s
        ErrorCategory.RATE_LIMIT: 3.0,  # Rate limit: 1s, 3s, 9s, 27s...
        ErrorCategory.PROVIDER_ERROR: 2.0,
        ErrorCategory.PARSE_ERROR: 1.0,  # No backoff needed
    }

    def __init__(
        self,
        max_retries: Optional[dict[ErrorCategory, int]] = None,
        backoff_factors: Optional[dict[ErrorCategory, float]] = None,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True
    ):
        """
        Initialize retry strategy.

        Args:
            max_retries: Custom retry counts by category
            backoff_factors: Custom backoff multipliers by category
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            jitter: Whether to add random jitter to backoff
        """
        self.max_retries = max_retries or self.DEFAULT_RETRIES.copy()
        self.backoff_factors = backoff_factors or self.BACKOFF_MULTIPLIERS.copy()
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.jitter = jitter

    async def execute_with_retry(
        self,
        operation: Callable[[], Any],
        operation_name: str = "operation",
        category: Optional[ErrorCategory] = None,
        on_retry: Optional[Callable[[int, Exception], None]] = None
    ) -> T:
        """
        Execute operation with smart retry.

        Args:
            operation: Async operation to execute
            operation_name: Name for logging
            category: Error category (if known)
            on_retry: Callback for retry events (attempt_number, exception)

        Returns:
            Operation result

        Raises:
            GerdsenAIError: If all retries exhausted
        """
        last_exception: Optional[Exception] = None
        attempt = 0

        while True:
            try:
                return await operation()

            except Exception as e:
                last_exception = e
                attempt += 1

                # Classify error if not already GerdsenAIError
                if isinstance(e, GerdsenAIError):
                    error_category = e.category
                    error_message = e.message
                else:
                    error_category, suggestion = classify_exception(e)
                    error_message = str(e)

                # Determine if we should retry
                max_attempts = self.max_retries.get(error_category, 1)

                if attempt > max_attempts:
                    logger.error(
                        f"{operation_name} failed after {attempt} attempts: {error_message}"
                    )
                    raise

                # Calculate backoff delay
                backoff_factor = self.backoff_factors.get(error_category, 2.0)
                delay = min(
                    self.initial_delay * (backoff_factor ** (attempt - 1)),
                    self.max_delay
                )

                # Add jitter if enabled
                if self.jitter:
                    import random
                    delay *= random.uniform(0.8, 1.2)

                logger.warning(
                    f"{operation_name} failed (attempt {attempt}/{max_attempts + 1}): "
                    f"{error_message}. Retrying in {delay:.1f}s..."
                )

                # Call retry callback if provided
                if on_retry:
                    try:
                        on_retry(attempt, e)
                    except Exception as callback_error:
                        logger.error(f"Retry callback failed: {callback_error}")

                # Wait before retry
                await asyncio.sleep(delay)

        # This should never be reached due to raise above
        if last_exception:
            raise last_exception

    async def execute_with_fallback(
        self,
        primary_operation: Callable[[], T],
        fallback_operation: Callable[[], T],
        operation_name: str = "operation"
    ) -> T:
        """
        Execute primary operation with fallback.

        Args:
            primary_operation: Primary operation to try
            fallback_operation: Fallback if primary fails
            operation_name: Name for logging

        Returns:
            Result from either primary or fallback
        """
        try:
            logger.debug(f"Attempting {operation_name} (primary)")
            return await primary_operation()

        except Exception as primary_error:
            logger.warning(
                f"{operation_name} primary failed: {primary_error}. "
                "Trying fallback..."
            )

            try:
                result = await fallback_operation()
                logger.info(f"{operation_name} succeeded using fallback")
                return result

            except Exception as fallback_error:
                logger.error(
                    f"{operation_name} fallback also failed: {fallback_error}"
                )
                raise GerdsenAIError(
                    message=f"Both primary and fallback {operation_name} failed",
                    category=ErrorCategory.UNKNOWN,
                    recoverable=False,
                    context={
                        "primary_error": str(primary_error),
                        "fallback_error": str(fallback_error)
                    }
                )

    async def execute_with_timeout(
        self,
        operation: Callable[[], T],
        timeout_seconds: float,
        operation_name: str = "operation"
    ) -> T:
        """
        Execute operation with timeout.

        Args:
            operation: Operation to execute
            timeout_seconds: Timeout in seconds
            operation_name: Name for logging

        Returns:
            Operation result

        Raises:
            TimeoutError: If operation times out
        """
        try:
            return await asyncio.wait_for(operation(), timeout=timeout_seconds)

        except asyncio.TimeoutError:
            from .errors import TimeoutError as GerdsenAITimeoutError

            raise GerdsenAITimeoutError(
                message=f"{operation_name} timed out",
                timeout_seconds=timeout_seconds
            )

    def should_retry(
        self,
        exception: Exception,
        attempt: int
    ) -> tuple[bool, float]:
        """
        Determine if an exception should trigger retry.

        Args:
            exception: The exception that occurred
            attempt: Current attempt number (1-indexed)

        Returns:
            (should_retry, delay_seconds) tuple
        """
        # Classify error
        if isinstance(exception, GerdsenAIError):
            category = exception.category
            recoverable = exception.recoverable
        else:
            category, _ = classify_exception(exception)
            recoverable = True

        # Check if we have retries left
        max_attempts = self.max_retries.get(category, 1)
        should_retry = recoverable and (attempt <= max_attempts)

        # Calculate delay
        if should_retry:
            backoff_factor = self.backoff_factors.get(category, 2.0)
            delay = min(
                self.initial_delay * (backoff_factor ** (attempt - 1)),
                self.max_delay
            )
        else:
            delay = 0.0

        return (should_retry, delay)


class CircuitBreaker:
    """
    Circuit breaker pattern for failing operations.

    Prevents repeated attempts when a service is known to be down.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again
            expected_exception: Exception type to track
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open

    async def call(
        self,
        operation: Callable[[], T],
        operation_name: str = "operation"
    ) -> T:
        """
        Execute operation through circuit breaker.

        Args:
            operation: Operation to execute
            operation_name: Name for logging

        Returns:
            Operation result

        Raises:
            Exception: If circuit is open or operation fails
        """
        import time

        # Check circuit state
        if self.state == "open":
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                logger.info(f"Circuit breaker: Attempting recovery for {operation_name}")
                self.state = "half_open"
            else:
                raise GerdsenAIError(
                    message=f"Circuit breaker is OPEN for {operation_name}",
                    category=ErrorCategory.PROVIDER_ERROR,
                    recoverable=False,
                    suggestion=f"Wait {self.recovery_timeout}s before retrying"
                )

        try:
            result = await operation()

            # Success - reset or close circuit
            if self.state == "half_open":
                logger.info(f"Circuit breaker: Recovered for {operation_name}")
                self.state = "closed"
                self.failure_count = 0

            return result

        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            # Check if we should open the circuit
            if self.failure_count >= self.failure_threshold:
                logger.error(
                    f"Circuit breaker: OPENED for {operation_name} "
                    f"after {self.failure_count} failures"
                )
                self.state = "open"

            raise
