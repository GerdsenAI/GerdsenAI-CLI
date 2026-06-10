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

    async def delete_by_path(self, name: str, path: str) -> None:
        pts = self.collections.get(name)
        if pts is not None:
            self.collections[name] = [
                p for p in pts if p["payload"].get("path") != path
            ]


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
    tmp_path.mkdir(parents=True, exist_ok=True)
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
# incremental re-indexing
# --------------------------------------------------------------------------- #


def _indexer(repo: Path, store: FakeStore, tmp_path: Path) -> RepoIndexer:
    return RepoIndexer(
        repo,
        store,  # type: ignore[arg-type]
        FakeBackend(),  # type: ignore[arg-type]
        manifest_dir=tmp_path / "manifest",
    )


@pytest.mark.asyncio
async def test_incremental_falls_back_to_full_build(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    store = FakeStore()
    indexer = _indexer(repo, store, tmp_path)

    # No manifest yet -> behaves like a full build.
    stats = await indexer.build_incremental()
    assert stats.files == 2
    assert stats.chunks > 0
    assert indexer.manifest_path.exists()


@pytest.mark.asyncio
async def test_incremental_skips_unchanged(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    store = FakeStore()
    indexer = _indexer(repo, store, tmp_path)

    await indexer.build()
    baseline = await store.count(indexer.collection)

    stats = await indexer.build_incremental()
    assert stats.files == 0  # nothing re-embedded
    assert stats.unchanged == 2
    assert stats.removed == 0
    assert await store.count(indexer.collection) == baseline  # unchanged


@pytest.mark.asyncio
async def test_incremental_reembeds_changed_file(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    store = FakeStore()
    indexer = _indexer(repo, store, tmp_path)
    await indexer.build()

    # Modify one file; its stale chunks should be replaced, the other untouched.
    (repo / "a.py").write_text("def changed():\n    return 99\n" * 4)

    stats = await indexer.build_incremental()
    assert stats.files == 1
    assert stats.unchanged == 1
    payloads = [p["payload"]["path"] for p in store.collections[indexer.collection]]
    assert "a.py" in payloads  # re-added
    # No duplicate stale chunks: every a.py chunk reflects the new content.
    a_texts = [
        p["payload"]["text"]
        for p in store.collections[indexer.collection]
        if p["payload"]["path"] == "a.py"
    ]
    assert all("changed" in t for t in a_texts)


@pytest.mark.asyncio
async def test_incremental_removes_deleted_file(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    store = FakeStore()
    indexer = _indexer(repo, store, tmp_path)
    await indexer.build()

    (repo / "README.md").unlink()

    stats = await indexer.build_incremental()
    assert stats.removed == 1
    paths = {p["payload"]["path"] for p in store.collections[indexer.collection]}
    assert "README.md" not in paths


@pytest.mark.asyncio
async def test_clear_removes_manifest(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    store = FakeStore()
    indexer = _indexer(repo, store, tmp_path)
    await indexer.build()
    assert indexer.manifest_path.exists()

    await indexer.clear()
    assert not indexer.manifest_path.exists()


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


def _persistent_client(client: MagicMock) -> MagicMock:
    """Patch target: httpx.AsyncClient(...) held persistently by the store."""
    client.is_closed = False
    factory = MagicMock(return_value=client)
    return factory


@pytest.mark.asyncio
async def test_qdrant_available_true() -> None:
    client = MagicMock()
    client.get = AsyncMock(return_value=MagicMock(status_code=200))
    with patch(
        "gerdsenai_cli.core.vector_store.httpx.AsyncClient",
        _persistent_client(client),
    ):
        assert await QdrantVectorStore().available() is True


@pytest.mark.asyncio
async def test_qdrant_available_false_on_error() -> None:
    client = MagicMock()
    client.get = AsyncMock(side_effect=OSError("connection refused"))
    with patch(
        "gerdsenai_cli.core.vector_store.httpx.AsyncClient",
        _persistent_client(client),
    ):
        assert await QdrantVectorStore().available() is False


@pytest.mark.asyncio
async def test_qdrant_client_is_reused_across_calls() -> None:
    """The pooled client is created once, not per call (the optimization)."""
    client = MagicMock()
    client.get = AsyncMock(return_value=MagicMock(status_code=200))
    factory = _persistent_client(client)
    with patch("gerdsenai_cli.core.vector_store.httpx.AsyncClient", factory):
        store = QdrantVectorStore()
        await store.available()
        await store.collection_exists("c")
        await store.collection_exists("c")
    assert factory.call_count == 1  # one client for all three calls


@pytest.mark.asyncio
async def test_qdrant_close_releases_and_recreates() -> None:
    """close() closes the pool; a later call transparently gets a new client."""
    first = MagicMock()
    first.get = AsyncMock(return_value=MagicMock(status_code=200))
    first.is_closed = False

    async def _close() -> None:
        first.is_closed = True

    first.aclose = AsyncMock(side_effect=_close)
    second = MagicMock()
    second.get = AsyncMock(return_value=MagicMock(status_code=200))
    second.is_closed = False

    factory = MagicMock(side_effect=[first, second])
    with patch("gerdsenai_cli.core.vector_store.httpx.AsyncClient", factory):
        store = QdrantVectorStore()
        await store.available()
        await store.close()
        first.aclose.assert_awaited_once()
        await store.close()  # idempotent: nothing left to close
        await store.available()  # recreated after close
    assert factory.call_count == 2


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

        async def build_incremental(self) -> IndexStats:
            return IndexStats(files=1, chunks=3, unchanged=4, removed=1)

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

    refresh = await cmd.execute({"action": "refresh", "query": ""})
    assert refresh.success and "1 changed file" in (refresh.message or "")

    update = await cmd.execute({"action": "update", "query": ""})
    assert update.success and "1 changed file" in (update.message or "")

    search = await cmd.execute({"action": "search", "query": "foo"})
    assert search.success and "result" in (search.message or "")

    status = await cmd.execute({"action": "status", "query": ""})
    assert status.success
