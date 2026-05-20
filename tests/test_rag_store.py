"""tests for repowiki.core.rag_store: round-trip save/load + bookkeeping."""

from __future__ import annotations

from pathlib import Path

import pytest

from repowiki.core.models import FileInfo, ProjectContext
from repowiki.core.rag import SimpleRAG, _fast_sha
from repowiki.core.rag_store import SCHEMA_VERSION, RagStore


def _proj() -> ProjectContext:
    return ProjectContext(
        name="t",
        root=".",
        files=[
            FileInfo(
                path="src/auth.py", size=10, language="python", lines=2,
                content="def authenticate_user(uid):\n    return uid\n",
            ),
            FileInfo(
                path="src/view.py", size=10, language="python", lines=2,
                content="def render_dashboard():\n    return 'ok'\n",
            ),
        ],
    )


@pytest.fixture
async def store(tmp_path: Path):
    s = RagStore(db_path=tmp_path / "indexes.db")
    await s.init()
    yield s
    await s.close()


@pytest.mark.asyncio
async def test_save_then_load_round_trips(tmp_path):
    s = RagStore(db_path=tmp_path / "indexes.db")
    await s.init()
    try:
        project = _proj()
        rag = SimpleRAG()
        rag.index(project)

        await s.save("proj-A", rag)
        loaded = await s.load("proj-A")

        assert loaded is not None
        # Same chunk count, same file map, same tuning knobs.
        assert len(loaded.chunks) == len(rag.chunks)
        assert set(loaded._file_sha.keys()) == set(rag._file_sha.keys())
        assert loaded._k1 == rag._k1
        assert loaded._b == rag._b
        assert loaded.max_chunk_lines == rag.max_chunk_lines
        # Retrieval still works on the reloaded index.
        hits = loaded.retrieve("authenticate", top_k=5)
        assert hits and hits[0].file_path == "src/auth.py"
    finally:
        await s.close()


@pytest.mark.asyncio
async def test_load_returns_none_for_unknown_project(tmp_path):
    s = RagStore(db_path=tmp_path / "indexes.db")
    await s.init()
    try:
        assert await s.load("never-saved") is None
    finally:
        await s.close()


@pytest.mark.asyncio
async def test_save_replaces_prior_snapshot(tmp_path):
    s = RagStore(db_path=tmp_path / "indexes.db")
    await s.init()
    try:
        project = _proj()
        rag = SimpleRAG()
        rag.index(project)
        await s.save("proj-A", rag)

        # Now save a much smaller index for the same project_id; the load
        # must reflect the new shape, not the old one.
        small = SimpleRAG()
        small.upsert_file(
            "tiny.py", sha=_fast_sha("x"), language="python",
            text="def only_one(): pass\n",
        )
        await s.save("proj-A", small)

        loaded = await s.load("proj-A")
        assert loaded is not None
        # Only the tiny.py path survived.
        assert set(loaded._file_sha.keys()) == {"tiny.py"}
    finally:
        await s.close()


@pytest.mark.asyncio
async def test_list_indexed_files_returns_paths_and_shas(tmp_path):
    s = RagStore(db_path=tmp_path / "indexes.db")
    await s.init()
    try:
        rag = SimpleRAG()
        rag.index(_proj())
        await s.save("proj-A", rag)

        files = await s.list_indexed_files("proj-A")
        assert set(files.keys()) == {"src/auth.py", "src/view.py"}
        # Every entry has a non-empty sha (we computed it during index()).
        assert all(v for v in files.values())
    finally:
        await s.close()


@pytest.mark.asyncio
async def test_load_drops_stale_schema(tmp_path, monkeypatch):
    """If the on-disk schema_version is older than SCHEMA_VERSION, load
    should refuse the snapshot rather than misinterpret rows -- the caller
    will rebuild from scratch."""
    s = RagStore(db_path=tmp_path / "indexes.db")
    await s.init()
    try:
        rag = SimpleRAG()
        rag.index(_proj())
        await s.save("proj-A", rag)

        # Mutate the stored schema_version to something the current code
        # would never produce.
        await s._db.execute(
            "UPDATE rag_meta SET schema_version = ? WHERE project_id = ?",
            (SCHEMA_VERSION + 1, "proj-A"),
        )
        await s._db.commit()

        assert await s.load("proj-A") is None
        # And the now-stale snapshot was cleaned up.
        files = await s.list_indexed_files("proj-A")
        assert files == {}
    finally:
        await s.close()
