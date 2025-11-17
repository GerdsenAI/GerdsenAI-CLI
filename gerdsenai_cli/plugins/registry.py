"""
Plugin Registry with Auto-Discovery.

Central system for plugin management, discovery, and lifecycle.

Design Principles:
- Auto-discovery: Automatically find and load plugins
- Lazy loading: Only load plugins when needed
- Hot reload: Support plugin reload without restart (future)
- Type-safe: Full type checking for all operations
- Configuration: User can enable/disable plugins
"""

import importlib
import logging
import pkgutil
from pathlib import Path
from typing import Any, Type

from ..config.settings import Settings
from .base import Plugin, PluginCategory, PluginMetadata

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Central registry for all plugins.

    Manages plugin discovery, loading, initialization, and lifecycle.
    """

    def __init__(self, settings: Settings | None = None):
        """
        Initialize plugin registry.

        Args:
            settings: Optional settings for plugin configuration
        """
        self.settings = settings
        self.plugins: dict[PluginCategory, dict[str, Plugin]] = {
            category: {} for category in PluginCategory
        }
        self._initialized_plugins: set[str] = set()
        self._plugin_configs: dict[str, dict[str, Any]] = {}

    def register(self, plugin: Plugin) -> None:
        """
        Register a plugin manually.

        Args:
            plugin: Plugin instance to register
        """
        category = plugin.metadata.category
        name = plugin.metadata.name

        if name in self.plugins[category]:
            logger.warning(
                f"Plugin {name} already registered in category {category.value}, "
                f"replacing..."
            )

        self.plugins[category][name] = plugin
        logger.info(
            f"Registered plugin: {name} (category: {category.value}, "
            f"version: {plugin.metadata.version})"
        )

    def unregister(self, category: PluginCategory, name: str) -> None:
        """
        Unregister a plugin.

        Args:
            category: Plugin category
            name: Plugin name
        """
        if name in self.plugins[category]:
            del self.plugins[category][name]
            if name in self._initialized_plugins:
                self._initialized_plugins.remove(name)
            logger.info(f"Unregistered plugin: {name}")

    def get(self, category: PluginCategory | str, name: str) -> Plugin:
        """
        Get plugin by category and name.

        Args:
            category: Plugin category (enum or string)
            name: Plugin name

        Returns:
            Plugin instance

        Raises:
            KeyError: If plugin not found
        """
        if isinstance(category, str):
            category = PluginCategory(category)

        if name not in self.plugins[category]:
            available = list(self.plugins[category].keys())
            raise KeyError(
                f"Plugin '{name}' not found in category '{category.value}'. "
                f"Available: {available}"
            )

        return self.plugins[category][name]

    def list_plugins(
        self,
        category: PluginCategory | str | None = None
    ) -> list[PluginMetadata]:
        """
        List all available plugins.

        Args:
            category: Optional category filter

        Returns:
            List of plugin metadata
        """
        if category is None:
            # List all plugins across all categories
            all_plugins = []
            for cat_plugins in self.plugins.values():
                all_plugins.extend([p.metadata for p in cat_plugins.values()])
            return all_plugins

        # List plugins in specific category
        if isinstance(category, str):
            category = PluginCategory(category)

        return [
            plugin.metadata
            for plugin in self.plugins[category].values()
        ]

    def is_available(self, category: PluginCategory | str, name: str) -> bool:
        """
        Check if plugin is available.

        Args:
            category: Plugin category
            name: Plugin name

        Returns:
            True if plugin is registered
        """
        if isinstance(category, str):
            category = PluginCategory(category)

        return name in self.plugins[category]

    async def initialize_plugin(
        self,
        category: PluginCategory | str,
        name: str
    ) -> bool:
        """
        Initialize a specific plugin.

        Args:
            category: Plugin category
            name: Plugin name

        Returns:
            True if initialization successful

        Raises:
            KeyError: If plugin not found
        """
        if isinstance(category, str):
            category = PluginCategory(category)

        plugin = self.get(category, name)
        plugin_id = f"{category.value}.{name}"

        if plugin_id in self._initialized_plugins:
            logger.debug(f"Plugin {plugin_id} already initialized")
            return True

        logger.info(f"Initializing plugin: {plugin_id}")

        try:
            success = await plugin.initialize()

            if success:
                self._initialized_plugins.add(plugin_id)
                logger.info(f"Plugin {plugin_id} initialized successfully")
            else:
                logger.error(f"Plugin {plugin_id} initialization failed")

            return success

        except Exception as e:
            logger.error(
                f"Plugin {plugin_id} initialization error: {e}",
                exc_info=True
            )
            return False

    async def initialize_all(self, category: PluginCategory | None = None) -> dict[str, bool]:
        """
        Initialize all plugins in a category or all categories.

        Args:
            category: Optional category filter

        Returns:
            Dictionary mapping plugin IDs to initialization success status
        """
        results = {}

        if category is None:
            # Initialize all plugins across all categories
            for cat in PluginCategory:
                for name in self.plugins[cat].keys():
                    plugin_id = f"{cat.value}.{name}"
                    results[plugin_id] = await self.initialize_plugin(cat, name)
        else:
            # Initialize plugins in specific category
            for name in self.plugins[category].keys():
                plugin_id = f"{category.value}.{name}"
                results[plugin_id] = await self.initialize_plugin(category, name)

        return results

    async def shutdown_all(self) -> None:
        """Shutdown all initialized plugins."""
        logger.info("Shutting down all plugins...")

        for plugin_id in list(self._initialized_plugins):
            try:
                category_str, name = plugin_id.split(".", 1)
                category = PluginCategory(category_str)
                plugin = self.get(category, name)

                await plugin.shutdown()
                logger.info(f"Plugin {plugin_id} shut down successfully")

            except Exception as e:
                logger.error(
                    f"Error shutting down plugin {plugin_id}: {e}",
                    exc_info=True
                )

        self._initialized_plugins.clear()
        logger.info("All plugins shut down")

    def discover_plugins(self, plugin_dir: Path) -> int:
        """
        Auto-discover plugins in directory.

        Scans directory for Python modules and looks for Plugin implementations.

        Args:
            plugin_dir: Directory to scan for plugins

        Returns:
            Number of plugins discovered
        """
        if not plugin_dir.exists():
            logger.warning(f"Plugin directory does not exist: {plugin_dir}")
            return 0

        discovered_count = 0

        logger.info(f"Discovering plugins in: {plugin_dir}")

        # Scan all subdirectories (vision, audio, video, etc.)
        for module_info in pkgutil.iter_modules([str(plugin_dir)]):
            try:
                # Import module
                module_name = f"gerdsenai_cli.plugins.{module_info.name}"
                module = importlib.import_module(module_name)

                # Look for Plugin implementations
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)

                    # Check if it's a Plugin class (not the Protocol itself)
                    if (
                        isinstance(attr, type)
                        and hasattr(attr, "metadata")
                        and attr_name not in ("Plugin", "VisionPlugin", "AudioPlugin", "VideoPlugin")
                    ):
                        try:
                            # Instantiate and register
                            plugin_instance = attr()
                            self.register(plugin_instance)
                            discovered_count += 1

                        except Exception as e:
                            logger.error(
                                f"Error instantiating plugin {attr_name}: {e}",
                                exc_info=True
                            )

            except Exception as e:
                logger.error(
                    f"Error importing plugin module {module_info.name}: {e}",
                    exc_info=True
                )

        logger.info(f"Discovered {discovered_count} plugins")
        return discovered_count

    async def health_check_all(self) -> dict[str, dict[str, Any]]:
        """
        Run health checks on all initialized plugins.

        Returns:
            Dictionary mapping plugin IDs to health check results
        """
        results = {}

        for plugin_id in self._initialized_plugins:
            try:
                category_str, name = plugin_id.split(".", 1)
                category = PluginCategory(category_str)
                plugin = self.get(category, name)

                health = await plugin.health_check()
                results[plugin_id] = health

            except Exception as e:
                results[plugin_id] = {
                    "status": "unhealthy",
                    "message": f"Health check failed: {e}",
                    "details": {}
                }

        return results

    def get_plugin_info(
        self,
        category: PluginCategory | str,
        name: str
    ) -> dict[str, Any]:
        """
        Get detailed information about a plugin.

        Args:
            category: Plugin category
            name: Plugin name

        Returns:
            Dictionary with plugin information
        """
        if isinstance(category, str):
            category = PluginCategory(category)

        plugin = self.get(category, name)
        plugin_id = f"{category.value}.{name}"

        return {
            "id": plugin_id,
            "metadata": {
                "name": plugin.metadata.name,
                "version": plugin.metadata.version,
                "category": plugin.metadata.category.value,
                "description": plugin.metadata.description,
                "author": plugin.metadata.author,
                "dependencies": plugin.metadata.dependencies,
                "capabilities": plugin.metadata.capabilities,
            },
            "initialized": plugin_id in self._initialized_plugins,
            "configuration": plugin.metadata.configuration,
        }


# Global plugin registry instance
plugin_registry = PluginRegistry()


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "PluginRegistry",
    "plugin_registry",
]
