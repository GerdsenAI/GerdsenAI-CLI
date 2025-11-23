"""
Input validation and sanitization utilities.

Provides comprehensive validation for user inputs, file paths,
configurations, and edge case handling.
"""

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..core.errors import ConfigurationError, ErrorCategory, GerdsenAIError


class InputValidator:
    """
    Comprehensive input validation and sanitization.

    Handles edge cases, security validation, and user input normalization.
    """

    # Dangerous patterns to block (SECURITY CRITICAL)
    # Comprehensive list covering shell injection, command execution, and file system attacks
    DANGEROUS_PATTERNS = [
        # Destructive commands
        r";\s*rm\s+-rf",  # Shell injection with rm
        r"&&\s*rm\s+-rf",
        r"\|\s*rm\s+-rf",
        # Command execution
        r"\|\s*sh",  # Pipe to shell
        r"\|\s*bash",
        r"\|\s*zsh",
        r";\s*sh\s",
        r"exec\s*\(",  # Direct execution
        r"eval\s*\(",  # Eval injection
        # File redirection attacks
        r">\s*/dev/",  # Writing to devices
        r">\s*/etc/",  # Writing to system config
        r"2>&1",  # stderr redirect (often in attacks)
        # Command substitution
        r"`[^`]+`",  # Backtick command substitution
        r"\$\([^\)]+\)",  # Dollar-paren substitution
        r"\$\{[^\}]+\}",  # Variable expansion
        # Network attacks
        r"\|\s*curl",  # Pipe to curl (data exfiltration)
        r"\|\s*wget",
        r"\|\s*nc\s",  # Netcat
        # Process manipulation
        r"kill\s+-9",  # Force kill processes
        r"pkill",
        r"killall",
        # Privilege escalation
        r"sudo\s+",  # Sudo usage
        r"su\s+",  # Switch user
        # File system traversal in commands
        r"\.\./",  # Directory traversal
        r"/etc/passwd",  # Common attack target
        r"/etc/shadow",
    ]

    # Maximum lengths for safety
    MAX_MESSAGE_LENGTH = 100000  # 100KB
    MAX_FILE_PATH_LENGTH = 4096
    MAX_MODEL_NAME_LENGTH = 256
    MAX_URL_LENGTH = 2048

    @classmethod
    def validate_user_input(
        cls, user_input: str, max_length: int | None = None
    ) -> str:
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

        # Normalize whitespace CAREFULLY - preserve newlines and structure
        # Only collapse excessive whitespace within lines and limit consecutive newlines
        sanitized = re.sub(r"[ \t]+", " ", user_input)  # Normalize spaces/tabs only
        sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)  # Max 2 consecutive newlines
        sanitized = sanitized.strip()  # Trim leading/trailing whitespace

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
            ) from e

        # Check length
        if len(str(path)) > cls.MAX_FILE_PATH_LENGTH:
            raise GerdsenAIError(
                message=f"File path too long ({len(str(path))} chars)",
                category=ErrorCategory.FILE_NOT_FOUND,
            )

        # Check for path traversal - SECURITY CRITICAL
        try:
            resolved = path.resolve()
            cwd = Path.cwd().resolve()

            # Use relative_to() for robust path validation (prevents symlink attacks)
            try:
                resolved.relative_to(cwd)
                # Path is safely within project directory
            except ValueError:
                # Path is outside project directory
                if allow_absolute_only and path.is_absolute():
                    # Explicitly allowed absolute paths (use with extreme caution)
                    # This should only be used for specific trusted operations
                    pass
                else:
                    raise GerdsenAIError(
                        message="Path outside project directory not allowed",
                        category=ErrorCategory.FILE_NOT_FOUND,
                        suggestion="Use paths relative to project directory",
                        context={
                            "attempted_path": str(resolved),
                            "project_root": str(cwd),
                            "allow_absolute": allow_absolute_only,
                        },
                    ) from None

        except GerdsenAIError:
            # Re-raise our own errors
            raise
        except Exception as e:
            raise GerdsenAIError(
                message=f"Cannot resolve path: {file_path}",
                category=ErrorCategory.FILE_NOT_FOUND,
                original_exception=e,
            ) from e

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
        if not re.match(r"^[\w\-:.]+$", model_name):
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
            if require_http and parsed.scheme not in ("http", "https"):
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
            dangerous_hosts = ["0.0.0.0", "::"]
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
        except ValueError as e:
            raise ConfigurationError(
                message=f"Port must be a number: {port}",
                config_key="llm_port",
            ) from e

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
        except ValueError as e:
            raise GerdsenAIError(
                message=f"Temperature must be a number: {temperature}",
                category=ErrorCategory.INVALID_REQUEST,
            ) from e

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

        Removes sensitive information including API keys, tokens, passwords,
        database credentials, and private keys before logging.

        Args:
            data: Data to sanitize
            max_length: Maximum length for output

        Returns:
            Sanitized string safe for logging
        """
        # Convert to string
        text = str(data)

        # Remove Bearer tokens (e.g., "Bearer sk-1234..." or "Bearer eyJ...")
        text = re.sub(
            r"Bearer\s+[\w\-\.]+", "Bearer [REDACTED]", text, flags=re.IGNORECASE
        )

        # Remove Authorization headers
        text = re.sub(
            r"Authorization:\s*[^\s,]+",
            "Authorization: [REDACTED]",
            text,
            flags=re.IGNORECASE,
        )

        # Remove API keys, tokens, passwords, secrets (key-value patterns)
        sensitive_keys = [
            r"api[_-]?key",
            r"token",
            r"password",
            r"passwd",
            r"secret",
            r"auth",
            r"credential",
        ]
        for key_pattern in sensitive_keys:
            # Matches: api_key: "value", apiKey="value", api-key=value, etc.
            text = re.sub(
                rf'{key_pattern}["\']?\s*[:=]\s*["\']?([\w\-\.]+)',
                rf"{key_pattern}: [REDACTED]",
                text,
                flags=re.IGNORECASE,
            )

        # Remove database connection strings
        # postgres://user:password@host/db, mysql://user:password@host/db
        text = re.sub(
            r"(postgres|mysql|mongodb|redis)://[\w\-\.]+:[\w\-\.]+@",
            r"\1://user:[REDACTED]@",
            text,
            flags=re.IGNORECASE,
        )

        # Remove private keys (PEM format)
        text = re.sub(
            r"-----BEGIN\s+\w+\s+KEY-----[\s\S]+?-----END\s+\w+\s+KEY-----",
            "[PRIVATE KEY REDACTED]",
            text,
            flags=re.IGNORECASE,
        )

        # Remove JWT tokens (three base64 parts separated by dots)
        text = re.sub(r"\beyJ[\w\-]+\.[\w\-]+\.[\w\-]+", "[JWT_TOKEN_REDACTED]", text)

        # Remove potential API keys (long alphanumeric strings 20+ chars)
        # But be less aggressive - only if it looks like a key pattern
        text = re.sub(
            r"\b(sk|pk|key|token)[\-_][\w\-]{20,}\b",
            "[API_KEY_REDACTED]",
            text,
            flags=re.IGNORECASE,
        )

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
        min_value: Any | None = None,
        max_value: Any | None = None,
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
        cls, data: dict, required_keys: list[str], config_name: str = "configuration"
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
