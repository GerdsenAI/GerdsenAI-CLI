"""Tests for local + Tailscale model discovery."""

from __future__ import annotations

from typing import Any

import pytest

from gerdsenai_cli.commands.discover import DiscoverCommand
from gerdsenai_cli.core.providers import tailscale
from gerdsenai_cli.core.providers.base import ProviderType
from gerdsenai_cli.core.providers.detector import DiscoveredProvider, ProviderDetector

# --------------------------------------------------------------------------- #
# Tailscale parsing helpers
# --------------------------------------------------------------------------- #


def test_first_ipv4_prefers_tailscale_range() -> None:
    ips = ["fd7a:115c:a1e0::1", "100.101.102.103", "192.168.1.5"]
    assert tailscale._first_ipv4(ips) == "100.101.102.103"


def test_first_ipv4_falls_back_to_plain_ipv4() -> None:
    assert tailscale._first_ipv4(["fd7a::1", "10.0.0.2"]) == "10.0.0.2"


def test_first_ipv4_none_when_only_ipv6() -> None:
    assert tailscale._first_ipv4(["fd7a:115c:a1e0::1"]) is None


def test_parse_status_extracts_online_peers() -> None:
    raw = """
    {
      "Peer": {
        "nodeA": {"HostName": "gpu-box", "OS": "linux", "Online": true,
                   "TailscaleIPs": ["100.64.0.1", "fd7a::1"]},
        "nodeB": {"HostName": "laptop", "OS": "macOS", "Online": false,
                   "TailscaleIPs": ["100.64.0.2"]},
        "nodeC": {"HostName": "no-ip", "Online": true, "TailscaleIPs": []}
      }
    }
    """
    peers = tailscale._parse_status(raw)
    assert len(peers) == 1
    assert peers[0].hostname == "gpu-box"
    assert peers[0].ip == "100.64.0.1"
    assert peers[0].os == "linux"


def test_parse_status_handles_garbage() -> None:
    assert tailscale._parse_status("not json") == []
    assert tailscale._parse_status("{}") == []


@pytest.mark.asyncio
async def test_get_peers_noop_without_cli(monkeypatch: Any) -> None:
    """No tailscale CLI -> empty list, no subprocess launched."""
    monkeypatch.setattr(tailscale.shutil, "which", lambda _name: None)
    assert await tailscale.get_tailscale_peers() == []


# --------------------------------------------------------------------------- #
# Detector
# --------------------------------------------------------------------------- #


class _FakeProvider:
    def __init__(self, ptype: ProviderType = ProviderType.OLLAMA) -> None:
        self._ptype = ptype

    def get_provider_type(self) -> ProviderType:
        return self._ptype

    async def list_models(self) -> list[Any]:
        class _M:
            name = "fake-model"

        return [_M()]


@pytest.mark.asyncio
async def test_discover_local_only(monkeypatch: Any) -> None:
    detector = ProviderDetector()
    fake = _FakeProvider()

    async def fake_scan(timeout: float = 2.0) -> list[tuple[str, Any]]:
        return [("http://localhost:11434", fake)]

    monkeypatch.setattr(detector, "scan_common_ports", fake_scan)
    # Pretend tailscale is unavailable.
    monkeypatch.setattr(
        "gerdsenai_cli.core.providers.detector.tailscale_available", lambda: False
    )

    found = await detector.discover()
    assert len(found) == 1
    assert found[0].url == "http://localhost:11434"
    assert found[0].source == "local"


@pytest.mark.asyncio
async def test_discover_dedupes_local_and_remote(monkeypatch: Any) -> None:
    detector = ProviderDetector()
    fake = _FakeProvider()

    async def fake_scan(timeout: float = 2.0) -> list[tuple[str, Any]]:
        return [("http://localhost:11434", fake)]

    async def fake_remote(timeout: float = 2.0) -> list[DiscoveredProvider]:
        return [
            DiscoveredProvider("http://localhost:11434", fake, "tailscale:peer"),
            DiscoveredProvider("http://100.64.0.1:11434", fake, "tailscale:gpu-box"),
        ]

    monkeypatch.setattr(detector, "scan_common_ports", fake_scan)
    monkeypatch.setattr(detector, "discover_tailscale", fake_remote)
    monkeypatch.setattr(
        "gerdsenai_cli.core.providers.detector.tailscale_available", lambda: True
    )

    found = await detector.discover()
    urls = [d.url for d in found]
    # localhost kept once (local), the unique peer added.
    assert urls == ["http://localhost:11434", "http://100.64.0.1:11434"]
    assert found[0].source == "local"


# --------------------------------------------------------------------------- #
# /discover command
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_discover_command_no_results(monkeypatch: Any) -> None:
    async def empty(self: Any, **kwargs: Any) -> list[DiscoveredProvider]:
        return []

    monkeypatch.setattr(ProviderDetector, "discover", empty)
    result = await DiscoverCommand().execute({})
    assert result.success
    assert "No providers" in (result.message or "")


@pytest.mark.asyncio
async def test_discover_command_lists_results(monkeypatch: Any) -> None:
    fake = _FakeProvider()

    async def one(self: Any, **kwargs: Any) -> list[DiscoveredProvider]:
        return [DiscoveredProvider("http://localhost:11434", fake, "local")]

    monkeypatch.setattr(ProviderDetector, "discover", one)
    result = await DiscoverCommand().execute({"--no-tailscale": True})
    assert result.success
    assert "Found 1 provider" in (result.message or "")


# ---------------------------------------------------------------------------
# First-run setup wiring (main.GerdsenAICLI)
# ---------------------------------------------------------------------------


def test_endpoint_from_provider_local() -> None:
    from types import SimpleNamespace

    from gerdsenai_cli.main import GerdsenAICLI

    dp = SimpleNamespace(url="http://127.0.0.1:11434")
    assert GerdsenAICLI._endpoint_from_provider(dp) == ("http", "127.0.0.1", 11434)


def test_endpoint_from_provider_tailnet() -> None:
    from types import SimpleNamespace

    from gerdsenai_cli.main import GerdsenAICLI

    dp = SimpleNamespace(url="https://100.64.0.5:1234")
    assert GerdsenAICLI._endpoint_from_provider(dp) == ("https", "100.64.0.5", 1234)


def test_endpoint_from_provider_defaults() -> None:
    from types import SimpleNamespace

    from gerdsenai_cli.main import GerdsenAICLI

    dp = SimpleNamespace(url="//myhost")
    assert GerdsenAICLI._endpoint_from_provider(dp) == ("http", "myhost", 11434)


@pytest.mark.asyncio
async def test_discover_servers_for_setup_noop_on_error(monkeypatch: Any) -> None:
    """Setup discovery degrades to [] (never raises) when detection fails."""
    from gerdsenai_cli.main import GerdsenAICLI

    def boom() -> Any:
        raise RuntimeError("no detector")

    monkeypatch.setattr("gerdsenai_cli.core.providers.detector.ProviderDetector", boom)
    app = object.__new__(GerdsenAICLI)  # bypass heavy __init__
    assert await app._discover_servers_for_setup() == []
