"""Minimal Qdrant client over its REST API (via httpx).

Deliberately dependency-free — uses the already-present ``httpx`` rather than the
``qdrant-client`` package. Every method degrades gracefully: ``available()``
returns ``False`` when Qdrant is not reachable and callers skip indexing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30.0


@dataclass(frozen=True)
class SearchHit:
    """A single search result."""

    score: float
    payload: dict[str, Any]


class QdrantVectorStore:
    """Thin async wrapper around the Qdrant REST API."""

    def __init__(
        self, base_url: str = "http://localhost:6333", timeout: float = _DEFAULT_TIMEOUT
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    async def available(self) -> bool:
        """Return True if a Qdrant server answers at the configured URL."""
        try:
            async with self._client() as client:
                resp = await client.get("/healthz")
                if resp.status_code == 200:
                    return True
                # Older builds may not expose /healthz; the root returns 200.
                resp = await client.get("/")
                return resp.status_code == 200
        except Exception as e:
            logger.debug(f"Qdrant not available at {self.base_url}: {e}")
            return False

    async def collection_exists(self, name: str) -> bool:
        try:
            async with self._client() as client:
                resp = await client.get(f"/collections/{name}")
                return resp.status_code == 200
        except Exception:
            return False

    async def ensure_collection(self, name: str, dim: int) -> None:
        """Create the collection (Cosine distance) if it does not exist."""
        if await self.collection_exists(name):
            return
        async with self._client() as client:
            resp = await client.put(
                f"/collections/{name}",
                json={"vectors": {"size": dim, "distance": "Cosine"}},
            )
            resp.raise_for_status()

    async def delete_by_path(self, name: str, path: str) -> None:
        """Remove all points for a given file path (used before re-indexing)."""
        async with self._client() as client:
            await client.post(
                f"/collections/{name}/points/delete",
                params={"wait": "true"},
                json={"filter": {"must": [{"key": "path", "match": {"value": path}}]}},
            )

    async def upsert(self, name: str, points: list[dict[str, Any]]) -> None:
        """Upsert points: each is {id, vector, payload}."""
        if not points:
            return
        async with self._client() as client:
            resp = await client.put(
                f"/collections/{name}/points",
                params={"wait": "true"},
                json={"points": points},
            )
            resp.raise_for_status()

    async def search(
        self, name: str, vector: list[float], limit: int = 5
    ) -> list[SearchHit]:
        async with self._client() as client:
            resp = await client.post(
                f"/collections/{name}/points/search",
                json={"vector": vector, "limit": limit, "with_payload": True},
            )
            resp.raise_for_status()
            results = resp.json().get("result") or []
        return [
            SearchHit(score=float(r.get("score", 0.0)), payload=r.get("payload") or {})
            for r in results
        ]

    async def count(self, name: str) -> int:
        try:
            async with self._client() as client:
                resp = await client.post(
                    f"/collections/{name}/points/count", json={"exact": True}
                )
                resp.raise_for_status()
                return int(resp.json().get("result", {}).get("count", 0))
        except Exception:
            return 0

    async def delete_collection(self, name: str) -> None:
        async with self._client() as client:
            await client.delete(f"/collections/{name}")
