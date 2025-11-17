"""
Input validation and sanitization utilities.

Provides comprehensive validation for user inputs, file paths,
configurations, and edge case handling.
"""

import re
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from ..core.errors import ConfigurationError, GerdsenAIError, ErrorCategory


class InputValidator:
    """
    Comprehensive input validation and sanitization.

    Handles edge cases, security validation, and user input normalization.
    """

    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        r";\s*rm\s+-rf",  # Shell injection
        r"&&\s*rm\s+-rf",
        r"\|\s*sh",
        r">\s*/dev/",
        r"`.*`",  # Command substitution
        r"\$\(.*\)",
    ]

    # Maximum lengths for safety
    MAX_MESSAGE_LENGTH = 100000  # 100KB
    MAX_FILE_PATH_LENGTH = 4096
    MAX_MODEL_NAME_LENGTH = 256
    MAX_URL_LENGTH = 2048

    @classmethod
    def validate_user_input(cls, user_input: str, max_length: Optional[int] = None) -> str:
        """
        Validate and sanitize user input.

        Args:
            user_input: Raw user input
            max_length: Maximum allowed length

        Returns:
            Sanitized input

        Raises:
            GerdsenAIError: If input is invalid
        """
        if not isinstance(user_input, str):
            raise GerdsenAIError(
                message="Input must be a string",
                category=ErrorCategory.INVALID_REQUEST,
                recoverable=False,
            )

        # Check length
        max_len = max_length or cls.MAX_MESSAGE_LENGTH
        if len(user_input) > max_len:
            raise GerdsenAIError(
                message=f"Input too long ({len(user_input)} chars, max {max_len})",
                category=ErrorCategory.INVALID_REQUEST,
                suggestion=f"Reduce input length to under {max_len} characters",
            )

        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, user_input, re.IGNORECASE):
                raise GerdsenAIError(
                    message="Input contains potentially dangerous pattern",
                    category=ErrorCategory.INVALID_REQUEST,
                    recoverable=False,
                    suggestion="Remove shell commands or dangerous patterns",
                )

        # Normalize whitespace
        sanitized = " ".join(user_input.split())

        return sanitized

    @classmethod
    def validate_file_path(
        cls,
        file_path: str | Path,
        must_exist: bool = False,
        must_be_file: bool = True,
        allow_absolute_only: bool = False,
    ) -> Path:
        """
        Validate and normalize file path.

        Args:
            file_path: File path to validate
            must_exist: Path must exist
            must_be_file: Path must be a file (not directory)
            allow_absolute_only: Only allow absolute paths

        Returns:
            Validated Path object

        Raises:
            GerdsenAIError: If path is invalid
        """
        if not file_path:
            raise GerdsenAIError(
                message="File path cannot be empty",
                category=ErrorCategory.FILE_NOT_FOUND,
            )

        # Convert to Path
        try:
            path = Path(file_path)
        except Exception as e:
            raise GerdsenAIError(
                message=f"Invalid file path: {file_path}",
                category=ErrorCategory.FILE_NOT_FOUND,
                original_exception=e,
            )

        # Check length
        if len(str(path)) > cls.MAX_FILE_PATH_LENGTH:
            raise GerdsenAIError(
                message=f"File path too long ({len(str(path))} chars)",
                category=ErrorCategory.FILE_NOT_FOUND,
            )

        # Check for path traversal
        try:
            resolved = path.resolve()

            # Ensure path doesn't escape project directory
            cwd = Path.cwd().resolve()
            if not str(resolved).startswith(str(cwd)):
                # Allow if it's an absolute path to a valid location
                if not path.is_absolute() or not allow_absolute_only:
                    raise GerdsenAIError(
                        message="Path traversal not allowed",
                        category=ErrorCategory.FILE_NOT_FOUND,
                        suggestion="Use paths relative to project directory",
                    )

        except Exception as e:
            raise GerdsenAIError(
                message=f"Cannot resolve path: {file_path}",
                category=ErrorCategory.FILE_NOT_FOUND,
                original_exception=e,
            )

        # Check existence
        if must_exist and not resolved.exists():
            raise GerdsenAIError(
                message=f"Path does not exist: {file_path}",
                category=ErrorCategory.FILE_NOT_FOUND,
                suggestion="Check the file path and try again",
            )

        # Check if file vs directory
        if must_exist and must_be_file and not resolved.is_file():
            raise GerdsenAIError(
                message=f"Path is not a file: {file_path}",
                category=ErrorCategory.FILE_NOT_FOUND,
                suggestion="Provide a file path, not a directory",
            )

        return resolved

    @classmethod
    def validate_model_name(cls, model_name: str) -> str:
        """
        Validate model name.

        Args:
            model_name: Model name to validate

        Returns:
            Validated model name

        Raises:
            GerdsenAIError: If model name is invalid
        """
        if not model_name or not model_name.strip():
            raise GerdsenAIError(
                message="Model name cannot be empty",
                category=ErrorCategory.MODEL_NOT_FOUND,
            )

        if len(model_name) > cls.MAX_MODEL_NAME_LENGTH:
            raise GerdsenAIError(
                message=f"Model name too long ({len(model_name)} chars)",
                category=ErrorCategory.MODEL_NOT_FOUND,
            )

        # Allow alphanumeric, dash, underscore, colon, dot
        if not re.match(r'^[\w\-:.]+$', model_name):
            raise GerdsenAIError(
                message=f"Invalid model name format: {model_name}",
                category=ErrorCategory.MODEL_NOT_FOUND,
                suggestion="Use alphanumeric characters, dash, underscore, colon, or dot",
            )

        return model_name.strip()

    @classmethod
    def validate_url(cls, url: str, require_http: bool = True) -> str:
        """
        Validate URL.

        Args:
            url: URL to validate
            require_http: Require http or https scheme

        Returns:
            Validated URL

        Raises:
            GerdsenAIError: If URL is invalid
        """
        if not url or not url.strip():
            raise ConfigurationError(
                message="URL cannot be empty",
                config_key="llm_server_url",
            )

        if len(url) > cls.MAX_URL_LENGTH:
            raise ConfigurationError(
                message=f"URL too long ({len(url)} chars)",
                config_key="llm_server_url",
            )

        try:
            parsed = urlparse(url)

            # Check scheme
            if require_http and parsed.scheme not in ('http', 'https'):
                raise ConfigurationError(
                    message=f"Invalid URL scheme: {parsed.scheme}",
                    config_key="llm_server_url",
                    suggestion="Use http:// or https://",
                )

            # Check hostname
            if not parsed.hostname:
                raise ConfigurationError(
                    message="URL must have a hostname",
                    config_key="llm_server_url",
                )

            # Block dangerous hostnames
            dangerous_hosts = ['0.0.0.0', '::']
            if parsed.hostname in dangerous_hosts:
                raise ConfigurationError(
                    message=f"Dangerous hostname: {parsed.hostname}",
                    config_key="llm_server_url",
                    suggestion="Use localhost or a specific IP address",
                )

            return url.strip()

        except Exception as e:
            raise ConfigurationError(
                message=f"Invalid URL: {url}",
                config_key="llm_server_url",
                suggestion="Provide a valid URL (e.g., http://localhost:11434)",
            ) from e

    @classmethod
    def validate_port(cls, port: int | str) -> int:
        """
        Validate port number.

        Args:
            port: Port number to validate

        Returns:
            Validated port number

        Raises:
            ConfigurationError: If port is invalid
        """
        try:
            port_int = int(port)
        except ValueError:
            raise ConfigurationError(
                message=f"Port must be a number: {port}",
                config_key="llm_port",
            )

        if port_int < 1 or port_int > 65535:
            raise ConfigurationError(
                message=f"Port out of range (1-65535): {port_int}",
                config_key="llm_port",
                suggestion="Use a port between 1 and 65535",
            )

        # Warn about privileged ports
        if port_int < 1024:
            # This is just a warning, not an error
            pass

        return port_int

    @classmethod
    def validate_temperature(cls, temperature: float) -> float:
        """
        Validate temperature parameter.

        Args:
            temperature: Temperature value

        Returns:
            Validated temperature

        Raises:
            GerdsenAIError: If temperature is invalid
        """
        try:
            temp = float(temperature)
        except ValueError:
            raise GerdsenAIError(
                message=f"Temperature must be a number: {temperature}",
                category=ErrorCategory.INVALID_REQUEST,
            )

        if temp < 0.0 or temp > 2.0:
            raise GerdsenAIError(
                message=f"Temperature out of range (0.0-2.0): {temp}",
                category=ErrorCategory.INVALID_REQUEST,
                suggestion="Use a value between 0.0 (deterministic) and 2.0 (creative)",
            )

        return temp

    @classmethod
    def sanitize_for_logging(cls, data: Any, max_length: int = 1000) -> str:
        """
        Sanitize data for safe logging.

        Removes sensitive information and truncates long strings.

        Args:
            data: Data to sanitize
            max_length: Maximum length for output

        Returns:
            Sanitized string safe for logging
        """
        # Convert to string
        text = str(data)

        # Remove potential API keys (pattern: alphanumeric 20+ chars)
        text = re.sub(r'\b[A-Za-z0-9]{20,}\b', '[REDACTED]', text)

        # Remove potential tokens
        text = re.sub(r'token["\']?\s*:\s*["\']?[\w-]+', 'token: [REDACTED]', text, flags=re.IGNORECASE)
        text = re.sub(r'api[_-]?key["\']?\s*:\s*["\']?[\w-]+', 'api_key: [REDACTED]', text, flags=re.IGNORECASE)

        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length] + f"... (truncated {len(text) - max_length} chars)"

        return text

    @classmethod
    def validate_config_value(
        cls,
        key: str,
        value: Any,
        expected_type: type,
        min_value: Optional[Any] = None,
        max_value: Optional[Any] = None,
    ) -> Any:
        """
        Validate configuration value.

        Args:
            key: Configuration key
            value: Value to validate
            expected_type: Expected type
            min_value: Minimum value (for numeric types)
            max_value: Maximum value (for numeric types)

        Returns:
            Validated value

        Raises:
            ConfigurationError: If value is invalid
        """
        # Type check
        if not isinstance(value, expected_type):
            raise ConfigurationError(
                message=f"{key} must be {expected_type.__name__}, got {type(value).__name__}",
                config_key=key,
            )

        # Range check for numeric types
        if expected_type in (int, float):
            if min_value is not None and value < min_value:
                raise ConfigurationError(
                    message=f"{key} must be >= {min_value}, got {value}",
                    config_key=key,
                )

            if max_value is not None and value > max_value:
                raise ConfigurationError(
                    message=f"{key} must be <= {max_value}, got {value}",
                    config_key=key,
                )

        return value

    @classmethod
    def validate_dict_structure(
        cls,
        data: dict,
        required_keys: list[str],
        config_name: str = "configuration"
    ) -> dict:
        """
        Validate dictionary structure.

        Args:
            data: Dictionary to validate
            required_keys: Required keys
            config_name: Name for error messages

        Returns:
            Validated dictionary

        Raises:
            ConfigurationError: If structure is invalid
        """
        if not isinstance(data, dict):
            raise ConfigurationError(
                message=f"{config_name} must be a dictionary",
            )

        missing_keys = [key for key in required_keys if key not in data]

        if missing_keys:
            raise ConfigurationError(
                message=f"{config_name} missing required keys: {', '.join(missing_keys)}",
                suggestion=f"Add missing keys: {', '.join(missing_keys)}",
            )

        return data
