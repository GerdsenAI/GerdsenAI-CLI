"""
Settings and configuration models for GerdsenAI CLI.

This module contains Pydantic models for configuration validation and management.
"""

from typing import Any, Dict, Optional
from pathlib import Path
from pydantic import BaseModel, Field, validator


class Settings(BaseModel):
    """Main settings configuration for GerdsenAI CLI."""
    
    # LLM Server Configuration
    llm_server_url: str = Field(
        default="http://localhost:11434",
        description="URL of the local LLM server"
    )
    
    current_model: str = Field(
        default="",
        description="Currently selected model name"
    )
    
    api_timeout: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="API timeout in seconds"
    )
    
    # User Preferences
    user_preferences: Dict[str, Any] = Field(
        default_factory=lambda: {
            "theme": "dark",
            "show_timestamps": True,
            "auto_save": True,
            "max_context_length": 4000,
            "temperature": 0.7,
            "top_p": 0.9
        },
        description="User preferences and UI settings"
    )
    
    # Optional advanced settings
    max_retries: int = Field(default=3, ge=0, le=10)
    debug_mode: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    
    @validator('llm_server_url')
    def validate_server_url(cls, v):
        """Validate the LLM server URL format."""
        if not v:
            raise ValueError("LLM server URL cannot be empty")
        
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError("LLM server URL must start with http:// or https://")
            
        return v.rstrip('/')
    
    @validator('current_model')
    def validate_model_name(cls, v):
        """Validate model name (can be empty for initial setup)."""
        return v.strip() if v else ""
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
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
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "forbid"
        json_encoders = {
            Path: str
        }
