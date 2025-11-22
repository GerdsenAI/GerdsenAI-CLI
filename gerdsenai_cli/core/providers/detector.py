"""
Provider Detection System.

Automatically detects which LLM provider is running at a given URL.
"""

import asyncio
import logging
from typing import Any, Optional

from ...constants import ProviderDefaults
from .base import LLMProvider, ProviderType
from .huggingface import HuggingFaceProvider
from .lm_studio import LMStudioProvider
from .ollama import OllamaProvider
from .vllm import VLLMProvider

logger = logging.getLogger(__name__)


class ProviderDetector:
    """
    Automatically detect which LLM provider is running.

    Scans common ports and URLs to find available providers.
    """

    # Detection order (try most specific first)
    PROVIDER_CLASSES = [
        OllamaProvider,  # Has unique /api/tags endpoint
        LMStudioProvider,  # Typically on port 1234
        HuggingFaceProvider,  # Has /info endpoint
        VLLMProvider,  # OpenAI-compatible, try last
    ]

    # Common configurations to try (using centralized ProviderDefaults)
    # Note: Extended with additional common ports beyond standard providers
    COMMON_CONFIGS = ProviderDefaults.get_common_configs() + [
        ("http://127.0.0.1:1234", "LM Studio (loopback)"),
        ("http://localhost:5000", "text-generation-webui"),
        ("http://localhost:5001", "KoboldAI"),
        ("http://localhost:8001", "Custom provider"),
    ]

    async def detect_provider(
        self, url: str, timeout: float = 5.0
    ) -> Optional[LLMProvider]:
        """
        Try to detect which provider is at the given URL.

        Args:
            url: Base URL to check
            timeout: Detection timeout in seconds

        Returns:
            Detected provider instance or None
        """
        logger.info(f"Detecting provider at {url}...")

        for provider_class in self.PROVIDER_CLASSES:
            try:
                provider = provider_class(url, timeout)
                if await provider.detect():
                    logger.info(f"✅ Detected {provider_class.__name__} at {url}")
                    return provider
            except Exception as e:
                logger.debug(f"Detection failed for {provider_class.__name__}: {e}")
                continue

        logger.warning(f"No known provider detected at {url}")
        return None

    async def scan_common_ports(
        self, timeout: float = 2.0
    ) -> list[tuple[str, LLMProvider]]:
        """
        Scan common ports for LLM providers.

        Args:
            timeout: Timeout for each check

        Returns:
            List of (url, provider) tuples for found providers
        """
        logger.info("Scanning common ports for LLM providers...")

        found_providers = []

        # Create detection tasks for all common configs
        tasks = []
        for url, description in self.COMMON_CONFIGS:
            task = self._check_url(url, description, timeout)
            tasks.append(task)

        # Run all checks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, tuple) and result[1] is not None:
                found_providers.append(result)

        if found_providers:
            logger.info(f"Found {len(found_providers)} provider(s)")
            for url, provider in found_providers:
                logger.info(f"  • {provider.__class__.__name__} at {url}")
        else:
            logger.warning("No providers found on common ports")

        return found_providers

    async def _check_url(
        self, url: str, description: str, timeout: float
    ) -> tuple[str, Optional[LLMProvider]]:
        """
        Check a single URL for providers.

        Args:
            url: URL to check
            description: Human-readable description
            timeout: Timeout in seconds

        Returns:
            (url, provider) tuple or (url, None) if not found
        """
        try:
            provider = await self.detect_provider(url, timeout)
            return (url, provider)
        except Exception as e:
            logger.debug(f"Check failed for {description}: {e}")
            return (url, None)

    async def get_best_provider(
        self, preference: Optional[ProviderType] = None
    ) -> Optional[LLMProvider]:
        """
        Get the best available provider.

        Args:
            preference: Preferred provider type (optional)

        Returns:
            Best available provider or None
        """
        providers = await self.scan_common_ports()

        if not providers:
            return None

        # If preference specified, try to find it
        if preference:
            for url, provider in providers:
                if provider and provider.get_provider_type() == preference:
                    return provider

        # Return first available provider
        return providers[0][1]

    def get_recommended_config(self, provider_type: ProviderType) -> dict[str, str]:
        """
        Get recommended configuration for a provider type.

        Args:
            provider_type: Type of provider

        Returns:
            Configuration dict with recommended settings
        """
        configs = {
            ProviderType.OLLAMA: {
                "protocol": "http",
                "llm_host": "localhost",
                "llm_port": "11434",
                "description": "Ollama (default configuration)",
            },
            ProviderType.LM_STUDIO: {
                "protocol": "http",
                "llm_host": "localhost",
                "llm_port": "1234",
                "description": "LM Studio (default configuration)",
            },
            ProviderType.VLLM: {
                "protocol": "http",
                "llm_host": "localhost",
                "llm_port": "8000",
                "description": "vLLM (default configuration)",
            },
            ProviderType.HUGGINGFACE_TGI: {
                "protocol": "http",
                "llm_host": "localhost",
                "llm_port": "8080",
                "description": "Hugging Face TGI (default configuration)",
            },
        }

        return configs.get(
            provider_type,
            {
                "protocol": "http",
                "llm_host": "localhost",
                "llm_port": "8080",
                "description": "Generic OpenAI-compatible provider",
            },
        )

    async def auto_configure(self) -> Optional[dict[str, str]]:
        """
        Automatically detect and configure the best provider.

        Returns:
            Configuration dict or None if no provider found
        """
        logger.info("Starting auto-configuration...")

        provider = await self.get_best_provider()

        if not provider:
            logger.error("No LLM providers found. Please ensure one is running.")
            return None

        provider_type = provider.get_provider_type()
        config = self.get_recommended_config(provider_type)

        # Override with actual detected URL
        from urllib.parse import urlparse

        parsed = urlparse(provider.base_url)

        config["protocol"] = parsed.scheme or "http"
        config["llm_host"] = parsed.hostname or "localhost"
        config["llm_port"] = str(parsed.port or 8080)

        logger.info(f"Auto-configured for {provider.__class__.__name__}")
        logger.info(f"  URL: {provider.base_url}")

        return config

    async def test_provider(self, provider: LLMProvider) -> dict[str, Any]:
        """
        Test a provider's functionality.

        Args:
            provider: Provider to test

        Returns:
            Test results dict with connection status, models, capabilities, and errors
        """
        results = {
            "connection": False,
            "models": [],
            "capabilities": None,
            "errors": [],
        }

        # Test connection
        try:
            results["connection"] = await provider.test_connection()
        except Exception as e:
            results["errors"].append(f"Connection test failed: {e}")

        # List models
        try:
            models = await provider.list_models()
            results["models"] = [m.name for m in models]
        except Exception as e:
            results["errors"].append(f"List models failed: {e}")

        # Get capabilities
        try:
            results["capabilities"] = provider.get_capabilities()
        except Exception as e:
            results["errors"].append(f"Get capabilities failed: {e}")

        return results

    def format_provider_info(
        self, provider: LLMProvider, test_results: Optional[dict] = None
    ) -> str:
        """
        Format provider information for display.

        Args:
            provider: Provider instance
            test_results: Optional test results

        Returns:
            Formatted string
        """
        lines = []
        lines.append(f"Provider: {provider.__class__.__name__}")
        lines.append(f"Type: {provider.get_provider_type().value}")
        lines.append(f"URL: {provider.base_url}")

        if test_results:
            lines.append(
                f"Connection: {'✅ OK' if test_results['connection'] else '❌ Failed'}"
            )

            if test_results["models"]:
                lines.append(f"Models: {len(test_results['models'])}")
                for model in test_results["models"][:3]:
                    lines.append(f"  • {model}")
                if len(test_results["models"]) > 3:
                    lines.append(f"  ... and {len(test_results['models']) - 3} more")

            caps = test_results["capabilities"]
            if caps:
                lines.append("Capabilities:")
                lines.append(
                    f"  • Streaming: {'✅' if caps.supports_streaming else '❌'}"
                )
                lines.append(f"  • Tools: {'✅' if caps.supports_tools else '❌'}")
                lines.append(f"  • Vision: {'✅' if caps.supports_vision else '❌'}")

            if test_results["errors"]:
                lines.append("Errors:")
                for error in test_results["errors"]:
                    lines.append(f"  ⚠️  {error}")

        return "\n".join(lines)
