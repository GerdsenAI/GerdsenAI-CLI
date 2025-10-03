"""
Settings and configuration models for GerdsenAI CLI.

This module contains Pydantic models for configuration validation and management.
"""

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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

    # Phase 8c: Dynamic Context Management
    model_context_window: int | None = Field(
        default=None,
        description="Context window size in tokens (auto-detected from model, user can override)",
    )
    context_window_usage: float = Field(
        default=0.8,
        ge=0.1,
        le=1.0,
        description="Percentage of context window to use (default 0.8 = 80% for context, 20% for response)",
    )
    auto_read_strategy: str = Field(
        default="smart",
        description="Strategy for auto-reading files: 'smart' (prioritized), 'whole_repo' (all files), 'iterative' (keep reading), 'off' (disabled)",
    )
    enable_file_summarization: bool = Field(
        default=True,
        description="Enable intelligent file summarization when files don't fit in context",
    )
    max_iterative_reads: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of iterations for iterative reading strategy",
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
            "streaming": True,  # Enable streaming responses by default
            "tui_mode": True,  # Enable enhanced TUI by default
        },
        description="User preferences and UI settings",
    )

    # Optional advanced settings
    max_retries: int = Field(default=3, ge=0, le=10)
    debug_mode: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    @field_validator("protocol", mode="before")
    def validate_protocol(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in {"http", "https"}:
            raise ValueError("Protocol must be 'http' or 'https'")
        return v

    @field_validator("llm_host")
    def validate_host(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("LLM host cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def sync_url_components(self):
        """Synchronize llm_server_url with protocol/host/port (both directions)."""
        try:
            # Build the URL from granular components
            constructed_url = f"{self.protocol}://{self.llm_host}:{self.llm_port}"

            # Check if llm_server_url was explicitly provided and differs from defaults
            # If it differs from constructed URL, parse it and update components
            if self.llm_server_url != "http://localhost:11434":  # Not the default
                parsed = urlparse(self.llm_server_url)
                if parsed.scheme and parsed.hostname and parsed.port:
                    if self.llm_server_url.rstrip("/") != constructed_url.rstrip("/"):
                        # Update granular fields from provided URL (prefer explicit URL)
                        # Use object.__setattr__ to bypass validate_assignment and prevent infinite loop
                        object.__setattr__(self, "protocol", parsed.scheme)
                        object.__setattr__(self, "llm_host", parsed.hostname)
                        object.__setattr__(self, "llm_port", parsed.port)
                        constructed_url = self.llm_server_url.rstrip("/")

            # Always set canonical URL (from final component values)
            object.__setattr__(self, "llm_server_url", constructed_url.rstrip("/"))
        except Exception:
            # Fallback: ensure trailing components removed
            object.__setattr__(self, "llm_server_url", self.llm_server_url.rstrip("/"))
        return self

    @field_validator("current_model")
    def validate_model_name(cls, v: str) -> str:
        """Validate model name (can be empty for initial setup)."""
        return v.strip() if v else ""

    @field_validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v_upper

    @field_validator("auto_read_strategy")
    def validate_auto_read_strategy(cls, v: str) -> str:
        """Validate auto-read strategy."""
        valid_strategies = ["smart", "whole_repo", "iterative", "off"]
        v_lower = v.lower().strip()
        if v_lower not in valid_strategies:
            raise ValueError(
                f"Auto-read strategy must be one of: {', '.join(valid_strategies)}"
            )
        return v_lower

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference value with optional default."""
        return self.user_preferences.get(key, default)

    def set_preference(self, key: str, value: Any) -> None:
        """Set a user preference value."""
        self.user_preferences[key] = value

    # Pydantic v2 model configuration
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        json_encoders={Path: str},
    )
