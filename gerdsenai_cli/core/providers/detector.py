"""
Provider Detection System.

Automatically detects which LLM provider is running at a given URL.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from ...constants import ProviderDefaults
from .base import LLMProvider, ProviderType
from .huggingface import HuggingFaceProvider
from .lm_studio import LMStudioProvider
from .ollama import OllamaProvider
from .tailscale import get_tailscale_peers, tailscale_available
from .vllm import VLLMProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiscoveredProvider:
    """A provider found during discovery, with where it was found."""

    url: str
    provider: LLMProvider
    source: str  # "local" or "tailscale:<hostname>"


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

    # Ports probed on remote hosts (e.g. Tailscale peers). Derived from the
    # canonical provider defaults so there is a single source of truth.
    PROVIDER_PORTS: list[int] = [
        int(cfg["port"]) for cfg in ProviderDefaults.CONFIGURATIONS.values()
    ]

    async def detect_provider(
        self, url: str, timeout: float = 5.0
    ) -> LLMProvider | None:
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

        found_providers: list[tuple[str, LLMProvider]] = []

        # Create detection tasks for all common configs
        tasks = []
        for url, description in self.COMMON_CONFIGS:
            task = self._check_url(url, description, timeout)
            tasks.append(task)

        # Run all checks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, tuple):
                url, provider = result
                if provider is not None:
                    found_providers.append((url, provider))

        if found_providers:
            logger.info(f"Found {len(found_providers)} provider(s)")
            for url, provider in found_providers:
                logger.info(f"  • {provider.__class__.__name__} at {url}")
        else:
            logger.warning("No providers found on common ports")

        return found_providers

    async def scan_hosts(
        self,
        hosts: list[str],
        ports: list[int] | None = None,
        timeout: float = 2.0,
    ) -> list[tuple[str, LLMProvider]]:
        """Probe a set of hosts on the provider ports for running servers.

        Args:
            hosts: Hostnames or IPs to probe.
            ports: Ports to try on each host (defaults to PROVIDER_PORTS).
            timeout: Per-URL timeout in seconds.

        Returns:
            List of (url, provider) tuples for providers that responded.
        """
        ports = ports or self.PROVIDER_PORTS
        tasks = [
            self._check_url(f"http://{host}:{port}", host, timeout)
            for host in hosts
            for port in ports
        ]
        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)
        found: list[tuple[str, LLMProvider]] = []
        for r in results:
            if isinstance(r, tuple):
                url, prov = r
                if prov is not None:
                    found.append((url, prov))
        return found

    async def discover_tailscale(
        self, timeout: float = 2.0
    ) -> list[DiscoveredProvider]:
        """Discover providers running on reachable Tailscale peers.

        No-op (returns ``[]``) when the tailscale CLI is unavailable or the
        tailnet is down.
        """
        peers = await get_tailscale_peers()
        if not peers:
            return []

        ip_to_host = {peer.ip: peer.hostname for peer in peers}
        found = await self.scan_hosts(list(ip_to_host), timeout=timeout)

        discovered: list[DiscoveredProvider] = []
        for url, provider in found:
            # Map the URL's host back to the peer hostname for display.
            host = urlparse(url).hostname or ""
            label = ip_to_host.get(host, host)
            discovered.append(
                DiscoveredProvider(
                    url=url, provider=provider, source=f"tailscale:{label}"
                )
            )
        return discovered

    async def discover(
        self, include_tailscale: bool = True, timeout: float = 2.0
    ) -> list[DiscoveredProvider]:
        """Discover all reachable providers: local first, then Tailscale peers.

        Args:
            include_tailscale: Also probe Tailscale peers when the CLI is present.
            timeout: Per-URL timeout in seconds.

        Returns:
            De-duplicated list of discovered providers (local entries first).
        """
        local = [
            DiscoveredProvider(url=url, provider=provider, source="local")
            for url, provider in await self.scan_common_ports(timeout=timeout)
        ]

        remote: list[DiscoveredProvider] = []
        if include_tailscale and tailscale_available():
            remote = await self.discover_tailscale(timeout=timeout)

        # De-duplicate by URL, keeping the first (local) occurrence.
        seen: set[str] = set()
        result: list[DiscoveredProvider] = []
        for item in local + remote:
            if item.url in seen:
                continue
            seen.add(item.url)
            result.append(item)
        return result

    async def _check_url(
        self, url: str, description: str, timeout: float
    ) -> tuple[str, LLMProvider | None]:
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
        self, preference: ProviderType | None = None
    ) -> LLMProvider | None:
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
            for _url, provider in providers:
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

    async def auto_configure(self) -> dict[str, str] | None:
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
        results: dict[str, Any] = {
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
        self, provider: LLMProvider, test_results: dict | None = None
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
