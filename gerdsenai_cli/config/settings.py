"""
Settings and configuration models for GerdsenAI CLI.

This module contains Pydantic models for configuration validation and management.
"""

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator, field_validator, ConfigDict


class Settings(BaseModel):
    """Main settings configuration for GerdsenAI CLI."""

    # LLM Server Configuration
    # Backward compatible full server URL (derived from protocol/host/port if not explicitly overridden)
    llm_server_url: str = Field(
        default="http://localhost:11434",
        description="Full URL of the local LLM server (auto-derived from protocol/host/port if those are changed)",
    )

    # New granular server components
    protocol: str = Field(
        default="http",
        description="Protocol used to access the local LLM server (http or https)",
    )
    llm_host: str = Field(
        default="localhost",
        description="Hostname or IP address of the local LLM server",
    )
    llm_port: int = Field(
        default=11434, ge=1, le=65535, description="Port number of the local LLM server"
    )

    current_model: str = Field(default="", description="Currently selected model name")

    api_timeout: float = Field(
        default=30.0, ge=1.0, le=300.0, description="API timeout in seconds"
    )

    # User Preferences
    user_preferences: dict[str, Any] = Field(
        default_factory=lambda: {
            "theme": "dark",
            "show_timestamps": True,
            "auto_save": True,
            "max_context_length": 4000,
            "temperature": 0.7,
            "top_p": 0.9,
        },
        description="User preferences and UI settings",
    )

    # Optional advanced settings
    max_retries: int = Field(default=3, ge=0, le=10)
    debug_mode: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    @field_validator("protocol")
    def validate_protocol(cls, v):
        v = v.lower().strip()
        if v not in {"http", "https"}:
            raise ValueError("Protocol must be 'http' or 'https'")
        return v

    @field_validator("llm_host")
    def validate_host(cls, v):
        if not v or not v.strip():
            raise ValueError("LLM host cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def sync_url_components(self):  # type: ignore
        """Synchronize llm_server_url with protocol/host/port (both directions)."""
        try:
            # If llm_server_url was provided explicitly and differs from constructed, parse it
            parsed = urlparse(self.llm_server_url)
            if parsed.scheme and parsed.hostname and parsed.port:
                constructed = f"{self.protocol}://{self.llm_host}:{self.llm_port}"
                if self.llm_server_url.rstrip("/") != constructed.rstrip("/"):
                    # Update granular fields from provided URL (prefer explicit URL)
                    self.protocol = parsed.scheme
                    self.llm_host = parsed.hostname
                    if parsed.port:
                        self.llm_port = parsed.port
            # Always regenerate canonical URL from granular components to ensure consistency
            self.llm_server_url = f"{self.protocol}://{self.llm_host}:{self.llm_port}"
        except Exception:
            # Fallback: ensure trailing components removed
            self.llm_server_url = self.llm_server_url.rstrip("/")
        return self

    @field_validator("current_model")
    def validate_model_name(cls, v):
        """Validate model name (can be empty for initial setup)."""
        return v.strip() if v else ""

    @field_validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v_upper

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference value with optional default."""
        return self.user_preferences.get(key, default)

    def set_preference(self, key: str, value: Any) -> None:
        """Set a user preference value."""
        self.user_preferences[key] = value

    # Pydantic v2 configuration
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        json_encoders={Path: str},
    )
