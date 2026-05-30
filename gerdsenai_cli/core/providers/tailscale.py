"""Tailscale peer discovery.

Enumerates reachable Tailscale peers so the provider detector can probe them
for LLM servers (Ollama / vLLM / LM Studio / HuggingFace TGI) running on other
machines in the tailnet.

This module is intentionally dependency-free and *degrades to a no-op* when the
``tailscale`` CLI is not installed or returns nothing. It never raises for the
common "tailscale not present / not running" cases.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import shutil
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Fixed, argument-only command (no shell) — safe from injection.
_STATUS_CMD = ["tailscale", "status", "--json"]
_DEFAULT_TIMEOUT = 5.0


@dataclass(frozen=True)
class TailscalePeer:
    """A reachable host on the tailnet."""

    hostname: str
    ip: str
    os: str = ""
    online: bool = True


def tailscale_available() -> bool:
    """Return True if the ``tailscale`` CLI is on PATH."""
    return shutil.which("tailscale") is not None


def _first_ipv4(ips: list[str]) -> str | None:
    """Pick the Tailscale IPv4 (100.x.y.z) from a peer's address list."""
    for ip in ips:
        if ip.startswith("100.") and ip.count(".") == 3:
            return ip
    # Fall back to the first plain IPv4-looking address.
    for ip in ips:
        if ip.count(".") == 3 and ":" not in ip:
            return ip
    return None


def _parse_status(raw: str) -> list[TailscalePeer]:
    """Parse ``tailscale status --json`` output into peers (online only)."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        logger.debug("Could not parse tailscale status JSON")
        return []

    peers: list[TailscalePeer] = []
    for node in (data.get("Peer") or {}).values():
        if not isinstance(node, dict):
            continue
        if not node.get("Online", False):
            continue
        ip = _first_ipv4(node.get("TailscaleIPs") or [])
        if not ip:
            continue
        hostname = node.get("HostName") or node.get("DNSName") or ip
        peers.append(
            TailscalePeer(
                hostname=str(hostname).rstrip("."),
                ip=ip,
                os=str(node.get("OS") or ""),
                online=True,
            )
        )
    return peers


async def get_tailscale_peers(timeout: float = _DEFAULT_TIMEOUT) -> list[TailscalePeer]:
    """Return online Tailscale peers, or an empty list if unavailable.

    Never raises for the expected "no tailscale" cases — returns ``[]`` instead.
    """
    if not tailscale_available():
        logger.debug("tailscale CLI not found; skipping tailnet discovery")
        return []

    try:
        proc = await asyncio.create_subprocess_exec(
            *_STATUS_CMD,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except (OSError, ValueError) as e:
        logger.debug(f"Failed to launch tailscale: {e}")
        return []

    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        logger.debug("tailscale status timed out")
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        return []

    if proc.returncode != 0 or not stdout:
        # tailscale installed but not up / not logged in.
        return []

    peers = _parse_status(stdout.decode("utf-8", errors="replace"))
    logger.info(f"Discovered {len(peers)} online Tailscale peer(s)")
    return peers
