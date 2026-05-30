"""Pluggable text-embedding backends for vector indexing.

Local-first and optional: prefers an Ollama embedding model (no extra
dependency), falling back to ``sentence-transformers`` if that optional package
is installed. ``get_embedding_backend`` returns ``None`` when nothing is
available, so callers can degrade to a no-op.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import httpx

if TYPE_CHECKING:
    from ..config.settings import Settings

logger = logging.getLogger(__name__)

_DEFAULT_OLLAMA_URL = "http://localhost:11434"
_PROBE_TIMEOUT = 10.0


@runtime_checkable
class EmbeddingBackend(Protocol):
    """A backend that turns texts into dense vectors."""

    name: str

    async def available(self) -> bool:
        """Return True if the backend can actually produce embeddings."""
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Raises on hard failure."""
        ...


class OllamaEmbeddingBackend:
    """Embeddings via a local Ollama server's REST API.

    Uses ``POST /api/embeddings`` which is supported across Ollama versions.
    """

    def __init__(
        self,
        model: str,
        base_url: str = _DEFAULT_OLLAMA_URL,
        timeout: float = 60.0,
        concurrency: int = 4,
    ) -> None:
        self.name = f"ollama:{model}"
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._sem = asyncio.Semaphore(concurrency)

    async def _embed_one(self, client: httpx.AsyncClient, text: str) -> list[float]:
        async with self._sem:
            resp = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
            )
        resp.raise_for_status()
        data = resp.json()
        vector = data.get("embedding")
        if not isinstance(vector, list) or not vector:
            raise ValueError("Ollama returned no embedding (is the model pulled?)")
        return [float(x) for x in vector]

    async def available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=_PROBE_TIMEOUT) as client:
                await self._embed_one(client, "ping")
            return True
        except Exception as e:
            logger.debug(f"Ollama embeddings unavailable: {e}")
            return False

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            return await asyncio.gather(*(self._embed_one(client, t) for t in texts))


class SentenceTransformerBackend:
    """Embeddings via the optional ``sentence-transformers`` package."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.name = f"sentence-transformers:{model_name}"
        self.model_name = model_name
        self._model: object | None = None

    def _load(self) -> object:
        if self._model is None:
            from sentence_transformers import (  # type: ignore[import-not-found]
                SentenceTransformer,
            )

            self._model = SentenceTransformer(self.model_name)
        return self._model

    async def available(self) -> bool:
        try:
            import importlib.util

            return importlib.util.find_spec("sentence_transformers") is not None
        except Exception:
            return False

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        def _run() -> list[list[float]]:
            model = self._load()
            # encode returns a numpy array; convert to plain Python floats.
            vectors = model.encode(texts, show_progress_bar=False)  # type: ignore[attr-defined]
            return [[float(x) for x in row] for row in vectors]

        return await asyncio.get_event_loop().run_in_executor(None, _run)


async def get_embedding_backend(settings: Settings) -> EmbeddingBackend | None:
    """Return the best available embedding backend, or None.

    Order: Ollama (local, no extra dep) -> sentence-transformers (optional).
    """
    ollama_url = settings.llm_server_url or _DEFAULT_OLLAMA_URL
    ollama = OllamaEmbeddingBackend(model=settings.embedding_model, base_url=ollama_url)
    if await ollama.available():
        logger.info(f"Using embedding backend: {ollama.name}")
        return ollama

    st = SentenceTransformerBackend()
    if await st.available():
        logger.info(f"Using embedding backend: {st.name}")
        return st

    logger.info(
        "No embedding backend available (Ollama embed model or sentence-transformers)"
    )
    return None
