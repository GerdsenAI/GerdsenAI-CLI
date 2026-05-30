"""Per-repository semantic index.

Chunks the repo's text files, embeds them with the configured backend, and
stores the vectors in a per-repo Qdrant collection for semantic search.

Everything here assumes the caller has already confirmed that both Qdrant and an
embedding backend are available (see ``build_indexer``); when either is missing
the higher-level command degrades to a no-op.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from .embeddings import EmbeddingBackend, get_embedding_backend
from .vector_store import QdrantVectorStore, SearchHit

if TYPE_CHECKING:
    from ..config.settings import Settings

logger = logging.getLogger(__name__)

# Fixed namespace for deterministic point IDs (uuid5).
_NAMESPACE = uuid.UUID("6f1c9b2a-3d4e-5a6b-7c8d-9e0f1a2b3c4d")

# Directories never worth indexing.
_IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".idea",
    ".vscode",
    "htmlcov",
    ".tox",
    "site-packages",
    ".next",
    "target",
}
# Text file extensions we index (keeps binaries out cheaply).
_TEXT_EXTS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cc",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".cs",
    ".swift",
    ".kt",
    ".scala",
    ".sh",
    ".bash",
    ".zsh",
    ".sql",
    ".md",
    ".rst",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".ini",
    ".cfg",
    ".html",
    ".css",
    ".scss",
    ".vue",
    ".lua",
}
_MAX_FILE_BYTES = 1_000_000  # skip very large files
_EMBED_BATCH = 64


@dataclass
class IndexStats:
    """Outcome of a build."""

    files: int = 0
    chunks: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class Chunk:
    path: str
    start_line: int
    end_line: int
    text: str


def collection_name_for(repo_root: Path) -> str:
    """Stable Qdrant collection name for a repository path."""
    digest = hashlib.sha1(str(repo_root.resolve()).encode("utf-8")).hexdigest()[:16]
    return f"repo_{digest}"


class RepoIndexer:
    """Builds and queries a per-repo vector index."""

    def __init__(
        self,
        repo_root: Path,
        store: QdrantVectorStore,
        backend: EmbeddingBackend,
        chunk_chars: int = 1200,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.store = store
        self.backend = backend
        self.chunk_chars = chunk_chars
        self.collection = collection_name_for(self.repo_root)

    # -- file gathering -------------------------------------------------- #

    def iter_text_files(self) -> list[Path]:
        """Return indexable text files under the repo root."""
        files: list[Path] = []
        for path in sorted(self.repo_root.rglob("*")):
            if not path.is_file():
                continue
            if any(part in _IGNORE_DIRS for part in path.parts):
                continue
            if path.suffix.lower() not in _TEXT_EXTS:
                continue
            try:
                if path.stat().st_size > _MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            files.append(path)
        return files

    def _chunk_file(self, path: Path) -> list[Chunk]:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []
        rel = str(path.relative_to(self.repo_root))

        chunks: list[Chunk] = []
        buf: list[str] = []
        buf_len = 0
        start_line = 1
        for i, line in enumerate(content.splitlines(keepends=True), start=1):
            buf.append(line)
            buf_len += len(line)
            if buf_len >= self.chunk_chars:
                text = "".join(buf).strip()
                if text:
                    chunks.append(Chunk(rel, start_line, i, text))
                buf, buf_len, start_line = [], 0, i + 1
        if buf:
            text = "".join(buf).strip()
            if text:
                end = start_line + len(buf) - 1
                chunks.append(Chunk(rel, start_line, end, text))
        return chunks

    # -- build / query --------------------------------------------------- #

    async def build(self) -> IndexStats:
        """Rebuild the index from scratch for this repo."""
        stats = IndexStats()
        files = self.iter_text_files()

        all_chunks: list[Chunk] = []
        for path in files:
            file_chunks = self._chunk_file(path)
            if file_chunks:
                stats.files += 1
                all_chunks.extend(file_chunks)
            else:
                stats.skipped += 1

        if not all_chunks:
            return stats

        # Fresh collection each build keeps results consistent.
        await self.store.delete_collection(self.collection)

        dim: int | None = None
        for start in range(0, len(all_chunks), _EMBED_BATCH):
            batch = all_chunks[start : start + _EMBED_BATCH]
            try:
                vectors = await self.backend.embed([c.text for c in batch])
            except Exception as e:
                stats.errors.append(f"embed failed: {e}")
                continue

            if dim is None and vectors:
                dim = len(vectors[0])
                await self.store.ensure_collection(self.collection, dim)

            points = [
                {
                    "id": str(uuid.uuid5(_NAMESPACE, f"{c.path}:{c.start_line}:{idx}")),
                    "vector": vec,
                    "payload": {
                        "path": c.path,
                        "start_line": c.start_line,
                        "end_line": c.end_line,
                        "text": c.text,
                    },
                }
                for idx, (c, vec) in enumerate(zip(batch, vectors, strict=False))
            ]
            try:
                await self.store.upsert(self.collection, points)
                stats.chunks += len(points)
            except Exception as e:
                stats.errors.append(f"upsert failed: {e}")

        return stats

    async def search(self, query: str, limit: int = 5) -> list[SearchHit]:
        """Return the most relevant chunks for a query."""
        vectors = await self.backend.embed([query])
        if not vectors:
            return []
        return await self.store.search(self.collection, vectors[0], limit=limit)

    async def status(self) -> dict[str, object]:
        return {
            "collection": self.collection,
            "exists": await self.store.collection_exists(self.collection),
            "points": await self.store.count(self.collection),
            "backend": self.backend.name,
        }

    async def clear(self) -> None:
        await self.store.delete_collection(self.collection)


async def build_indexer(settings: Settings, repo_root: Path) -> RepoIndexer | None:
    """Construct a RepoIndexer if Qdrant and an embedding backend are available.

    Returns ``None`` (no-op) when Qdrant is unreachable or no embedding backend
    exists. The ``enable_vector_index`` setting gates *automatic* retrieval in
    the agent flow; the explicit ``/index`` command opts in regardless.
    """
    store = QdrantVectorStore(settings.qdrant_url)
    if not await store.available():
        logger.info("Qdrant not reachable; vector indexing unavailable")
        return None

    backend = await get_embedding_backend(settings)
    if backend is None:
        return None

    return RepoIndexer(
        repo_root=repo_root,
        store=store,
        backend=backend,
        chunk_chars=settings.vector_index_chunk_chars,
    )
