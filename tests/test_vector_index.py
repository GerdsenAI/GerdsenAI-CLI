"""Tests for per-repo vector indexing (embeddings, Qdrant store, /index)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gerdsenai_cli.commands import index as index_mod
from gerdsenai_cli.commands.index import IndexCommand
from gerdsenai_cli.core.embeddings import OllamaEmbeddingBackend
from gerdsenai_cli.core.repo_index import (
    IndexStats,
    RepoIndexer,
    collection_name_for,
)
from gerdsenai_cli.core.vector_store import QdrantVectorStore, SearchHit


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #


class FakeBackend:
    name = "fake"

    async def available(self) -> bool:
        return True

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Deterministic 3-d vectors derived from text length.
        return [[float(len(t)), 1.0, 0.0] for t in texts]


class FakeStore:
    """In-memory stand-in for QdrantVectorStore."""

    def __init__(self) -> None:
        self.collections: dict[str, list[dict[str, Any]]] = {}

    async def available(self) -> bool:
        return True

    async def collection_exists(self, name: str) -> bool:
        return name in self.collections

    async def ensure_collection(self, name: str, dim: int) -> None:
        self.collections.setdefault(name, [])

    async def delete_collection(self, name: str) -> None:
        self.collections.pop(name, None)

    async def upsert(self, name: str, points: list[dict[str, Any]]) -> None:
        self.collections.setdefault(name, []).extend(points)

    async def search(
        self, name: str, vector: list[float], limit: int = 5
    ) -> list[SearchHit]:
        pts = self.collections.get(name, [])[:limit]
        return [SearchHit(score=1.0, payload=p["payload"]) for p in pts]

    async def count(self, name: str) -> int:
        return len(self.collections.get(name, []))


# --------------------------------------------------------------------------- #
# collection naming
# --------------------------------------------------------------------------- #


def test_collection_name_stable_and_valid() -> None:
    a = collection_name_for(Path("/tmp/repo"))
    b = collection_name_for(Path("/tmp/repo"))
    assert a == b
    assert a.startswith("repo_")
    assert all(c.isalnum() or c == "_" for c in a)


# --------------------------------------------------------------------------- #
# RepoIndexer
# --------------------------------------------------------------------------- #


def _make_repo(tmp_path: Path) -> Path:
    (tmp_path / "a.py").write_text("def foo():\n    return 1\n" * 5)
    (tmp_path / "README.md").write_text("# Title\n\nSome docs here.\n")
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n")  # binary, skipped
    sub = tmp_path / "node_modules"
    sub.mkdir()
    (sub / "skip.js").write_text("console.log('nope')\n")  # ignored dir
    return tmp_path


def test_iter_text_files_filters(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    indexer = RepoIndexer(repo, FakeStore(), FakeBackend())  # type: ignore[arg-type]
    names = {p.name for p in indexer.iter_text_files()}
    assert names == {"a.py", "README.md"}  # no png, no node_modules


def test_chunk_file_tracks_lines(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    indexer = RepoIndexer(repo, FakeStore(), FakeBackend(), chunk_chars=20)  # type: ignore[arg-type]
    chunks = indexer._chunk_file(repo / "a.py")
    assert chunks
    assert chunks[0].start_line == 1
    assert all(c.end_line >= c.start_line for c in chunks)


@pytest.mark.asyncio
async def test_build_and_search(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    store = FakeStore()
    indexer = RepoIndexer(repo, store, FakeBackend())  # type: ignore[arg-type]

    stats = await indexer.build()
    assert isinstance(stats, IndexStats)
    assert stats.files == 2
    assert stats.chunks > 0
    assert not stats.errors
    assert await store.count(indexer.collection) == stats.chunks

    hits = await indexer.search("foo", limit=3)
    assert hits
    assert "path" in hits[0].payload


# --------------------------------------------------------------------------- #
# build_indexer availability gating
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_build_indexer_none_when_qdrant_down(
    monkeypatch: Any, tmp_path: Path
) -> None:
    from gerdsenai_cli.config.settings import Settings
    from gerdsenai_cli.core import repo_index

    monkeypatch.setattr(QdrantVectorStore, "available", AsyncMock(return_value=False))
    result = await repo_index.build_indexer(Settings(), tmp_path)
    assert result is None


@pytest.mark.asyncio
async def test_build_indexer_none_when_no_backend(
    monkeypatch: Any, tmp_path: Path
) -> None:
    from gerdsenai_cli.config.settings import Settings
    from gerdsenai_cli.core import repo_index

    monkeypatch.setattr(QdrantVectorStore, "available", AsyncMock(return_value=True))
    monkeypatch.setattr(
        repo_index, "get_embedding_backend", AsyncMock(return_value=None)
    )
    result = await repo_index.build_indexer(Settings(), tmp_path)
    assert result is None


# --------------------------------------------------------------------------- #
# Thin wrappers (mocked httpx)
# --------------------------------------------------------------------------- #


def _mock_async_client(client: Any) -> Any:
    """Patch target: httpx.AsyncClient(...) used as `async with ... as c`."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=cm)
    return factory


@pytest.mark.asyncio
async def test_qdrant_available_true() -> None:
    client = MagicMock()
    client.get = AsyncMock(return_value=MagicMock(status_code=200))
    with patch(
        "gerdsenai_cli.core.vector_store.httpx.AsyncClient", _mock_async_client(client)
    ):
        assert await QdrantVectorStore().available() is True


@pytest.mark.asyncio
async def test_qdrant_available_false_on_error() -> None:
    client = MagicMock()
    client.get = AsyncMock(side_effect=OSError("connection refused"))
    with patch(
        "gerdsenai_cli.core.vector_store.httpx.AsyncClient", _mock_async_client(client)
    ):
        assert await QdrantVectorStore().available() is False


@pytest.mark.asyncio
async def test_ollama_embed_parses_vector() -> None:
    client = MagicMock()
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
    resp.raise_for_status = MagicMock()
    client.post = AsyncMock(return_value=resp)
    with patch(
        "gerdsenai_cli.core.embeddings.httpx.AsyncClient", _mock_async_client(client)
    ):
        out = await OllamaEmbeddingBackend("nomic-embed-text").embed(["hello"])
    assert out == [[0.1, 0.2, 0.3]]


# --------------------------------------------------------------------------- #
# /index command
# --------------------------------------------------------------------------- #


def test_parse_arguments_variants() -> None:
    cmd = IndexCommand()
    assert cmd.parse_arguments("") == {"action": "status", "query": ""}
    assert cmd.parse_arguments("build") == {"action": "build", "query": ""}
    assert cmd.parse_arguments("search foo bar") == {
        "action": "search",
        "query": "foo bar",
    }
    # Bare text with no known action -> treated as a search query.
    assert cmd.parse_arguments("where is auth") == {
        "action": "search",
        "query": "where is auth",
    }


@pytest.mark.asyncio
async def test_index_command_unavailable(monkeypatch: Any) -> None:
    monkeypatch.setattr(index_mod, "build_indexer", AsyncMock(return_value=None))
    result = await IndexCommand().execute({"action": "status", "query": ""})
    assert result.success
    assert "unavailable" in (result.message or "").lower()


@pytest.mark.asyncio
async def test_index_command_build_and_search(monkeypatch: Any) -> None:
    class FakeIndexer:
        collection = "repo_test"

        async def build(self) -> IndexStats:
            return IndexStats(files=2, chunks=7)

        async def search(self, query: str, limit: int = 5) -> list[SearchHit]:
            return [
                SearchHit(
                    score=0.9, payload={"path": "a.py", "start_line": 1, "text": "x"}
                )
            ]

        async def status(self) -> dict[str, object]:
            return {
                "collection": "repo_test",
                "exists": True,
                "points": 7,
                "backend": "fake",
            }

        async def clear(self) -> None:
            return None

    monkeypatch.setattr(
        index_mod, "build_indexer", AsyncMock(return_value=FakeIndexer())
    )
    cmd = IndexCommand()

    build = await cmd.execute({"action": "build", "query": ""})
    assert build.success and "7 chunks" in (build.message or "")

    search = await cmd.execute({"action": "search", "query": "foo"})
    assert search.success and "result" in (search.message or "")

    status = await cmd.execute({"action": "status", "query": ""})
    assert status.success
