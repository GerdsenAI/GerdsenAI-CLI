"""
Configuration manager for GerdsenAI CLI.

This module handles loading, saving, and managing configuration files.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from rich.console import Console

from ..utils.display import show_error, show_info, show_warning
from .settings import Settings

console = Console()


class ConfigManager:
    """Manages configuration file operations."""

    def __init__(self, config_path: str | None = None):
        """
        Initialize the configuration manager.

        Args:
            config_path: Optional custom path to config file
        """
        if config_path:
            self.config_file = Path(config_path)
        else:
            # Default config location
            config_dir = Path.home() / ".config" / "gerdsenai-cli"
            config_dir.mkdir(parents=True, exist_ok=True)
            self.config_file = config_dir / "config.json"

        self.backup_dir = self.config_file.parent / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    async def load_settings(self) -> Settings | None:
        """
        Load settings from configuration file.

        Returns:
            Settings object if successful, None if file doesn't exist or invalid
        """
        try:
            if not self.config_file.exists():
                return None

            # Read config file asynchronously
            loop = asyncio.get_event_loop()
            config_data = await loop.run_in_executor(
                None, self.config_file.read_text, "utf-8"
            )

            # Parse JSON
            config_dict = json.loads(config_data)

            # Create Settings object with validation
            settings = Settings(**config_dict)

            return settings

        except json.JSONDecodeError as e:
            show_error(f"Invalid JSON in config file: {e}")
            await self._backup_corrupted_config()
            return None
        except Exception as e:
            show_error(f"Failed to load configuration: {e}")
            return None

    async def save_settings(self, settings: Settings) -> bool:
        """
        Save settings to configuration file.

        Args:
            settings: Settings object to save

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup if config exists
            if self.config_file.exists():
                await self._create_backup()

            # Convert settings to dictionary
            config_dict = settings.dict()

            # Add metadata
            config_dict["_metadata"] = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "application": "GerdsenAI CLI",
            }

            # Write config file asynchronously
            loop = asyncio.get_event_loop()
            config_json = json.dumps(config_dict, indent=2, ensure_ascii=False)

            await loop.run_in_executor(
                None, self.config_file.write_text, config_json, "utf-8"
            )

            return True

        except Exception as e:
            show_error(f"Failed to save configuration: {e}")
            return False

    async def _create_backup(self) -> None:
        """Create a backup of the current config file."""
        try:
            if not self.config_file.exists():
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"config_backup_{timestamp}.json"

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self._copy_file, self.config_file, backup_file
            )

            # Keep only last 5 backups
            await self._cleanup_old_backups()

        except Exception as e:
            show_warning(f"Failed to create config backup: {e}")

    async def _backup_corrupted_config(self) -> None:
        """Backup a corrupted config file for debugging."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"corrupted_config_{timestamp}.json"

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self._copy_file, self.config_file, backup_file
            )

            show_info(f"Corrupted config backed up to: {backup_file}")

        except Exception as e:
            show_warning(f"Failed to backup corrupted config: {e}")

    def _copy_file(self, source: Path, destination: Path) -> None:
        """Copy a file synchronously."""
        destination.write_bytes(source.read_bytes())

    async def _cleanup_old_backups(self, keep_count: int = 5) -> None:
        """Remove old backup files, keeping only the most recent ones."""
        try:
            backup_files = list(self.backup_dir.glob("config_backup_*.json"))
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

            # Remove old backups
            for old_backup in backup_files[keep_count:]:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, old_backup.unlink)

        except Exception as e:
            show_warning(f"Failed to cleanup old backups: {e}")

    def get_config_path(self) -> Path:
        """Get the current config file path."""
        return self.config_file

    async def reset_config(self) -> bool:
        """
        Reset configuration to defaults.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup first
            if self.config_file.exists():
                await self._create_backup()

            # Create default settings
            default_settings = Settings()

            # Save default settings
            return await self.save_settings(default_settings)

        except Exception as e:
            show_error(f"Failed to reset configuration: {e}")
            return False

    async def validate_config(self) -> tuple[bool, str | None]:
        """
        Validate the current configuration file.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            settings = await self.load_settings()
            if settings is None:
                return False, "Configuration file not found or invalid"

            return True, None

        except Exception as e:
            return False, str(e)
