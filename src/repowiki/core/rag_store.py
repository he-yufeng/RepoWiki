"""SQLite-backed persistence for :class:`repowiki.core.rag.SimpleRAG`.

The chat RAG used to rebuild itself from scratch every time the server
restarted -- O(n) tokenisation on every cold start, even when nothing in
the project had changed. This module persists the index so:

  - A repeat scan with ``--since`` only re-chunks the changed files.
  - A server restart can reload an existing index in milliseconds.
  - Wiki-page chunks live alongside code chunks under a ``kind`` flag so
    chat queries can target either.

The DB lives next to the analyzer cache at
``~/.repowiki/indexes.db``. A separate file (rather than reusing the
analyzer's ``cache.db``) means a user who wants to wipe the chat index
without losing the wiki cache can ``rm`` one file.
"""

from __future__ import annotations

import json
import pickle
from collections import Counter
from pathlib import Path

import aiosqlite

from repowiki.core.rag import Chunk, SimpleRAG

_INDEX_DIR = Path.home() / ".repowiki"
_INDEX_DB = _INDEX_DIR / "indexes.db"

# Bump this when the table layout changes; ``load`` will drop+rebuild
# anything stamped with a different version rather than misinterpret it.
SCHEMA_VERSION = 1


class RagStore:
    """async, project-scoped persistence layer for SimpleRAG."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path or _INDEX_DB)
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        _INDEX_DIR.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS rag_files (
                project_id TEXT NOT NULL,
                path       TEXT NOT NULL,
                sha        TEXT NOT NULL,
                kind       TEXT NOT NULL,
                PRIMARY KEY (project_id, path)
            );
            CREATE TABLE IF NOT EXISTS rag_chunks (
                project_id TEXT    NOT NULL,
                chunk_id   INTEGER NOT NULL,
                path       TEXT    NOT NULL,
                line_start INTEGER NOT NULL,
                line_end   INTEGER NOT NULL,
                content    TEXT    NOT NULL,
                kind       TEXT    NOT NULL,
                length     INTEGER NOT NULL,
                tf_blob    BLOB    NOT NULL,
                PRIMARY KEY (project_id, chunk_id)
            );
            CREATE TABLE IF NOT EXISTS rag_meta (
                project_id     TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                doc_count      INTEGER NOT NULL,
                avgdl          REAL    NOT NULL,
                k1             REAL    NOT NULL,
                b              REAL    NOT NULL,
                max_chunk_lines    INTEGER NOT NULL,
                soft_chunk_lines   INTEGER NOT NULL,
                overlap_lines      INTEGER NOT NULL,
                idf_blob       BLOB    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS rag_chunks_by_project
                ON rag_chunks (project_id, chunk_id);
            """
        )
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    # ---------- file-level helpers (used by incremental scan) ----------

    async def list_indexed_files(self, project_id: str) -> dict[str, str]:
        """return ``{path: sha}`` for every file currently in the index.

        Callers diff this against the current project's content hashes to
        decide what to upsert and what to delete.
        """
        if not self._db:
            return {}
        cur = await self._db.execute(
            "SELECT path, sha FROM rag_files WHERE project_id = ?",
            (project_id,),
        )
        rows = await cur.fetchall()
        return {row[0]: row[1] for row in rows}

    async def delete_project(self, project_id: str) -> None:
        if not self._db:
            return
        for table in ("rag_files", "rag_chunks", "rag_meta"):
            await self._db.execute(
                f"DELETE FROM {table} WHERE project_id = ?", (project_id,)
            )
        await self._db.commit()

    # ---------- whole-RAG save / load ----------

    async def save(self, project_id: str, rag: SimpleRAG) -> None:
        """write the entire RAG snapshot for ``project_id`` atomically.

        We don't try to apply per-chunk diffs to the DB because the
        in-memory ``SimpleRAG`` already recomputes everything on
        ``rebuild_global``; persisting the result wholesale keeps the
        load path simple (one query per table) at the cost of a full
        re-write per save. With <50k chunks for a 5k-file repo this is
        still well under a second.
        """
        if not self._db:
            return

        await self.delete_project(project_id)

        # Files table: one row per indexed file with its content hash.
        # We reconstruct (path, kind) from the chunks themselves -- the
        # rag instance only stores the sha map.
        path_kind: dict[str, str] = {}
        for chunk in rag.chunks:
            path_kind.setdefault(chunk.file_path, chunk.kind)
        await self._db.executemany(
            "INSERT INTO rag_files (project_id, path, sha, kind) VALUES (?, ?, ?, ?)",
            [
                (project_id, path, rag._file_sha.get(path, ""), path_kind.get(path, "code"))
                for path in rag._file_to_chunks
            ],
        )

        # Chunks + TF vectors (one row per chunk; tf serialized as JSON).
        chunk_rows = []
        for idx, chunk in enumerate(rag.chunks):
            tf = rag._tf_vectors[idx]
            length = rag._chunk_lens[idx]
            chunk_rows.append(
                (
                    project_id,
                    idx,
                    chunk.file_path,
                    chunk.line_start,
                    chunk.line_end,
                    chunk.content,
                    chunk.kind,
                    length,
                    json.dumps(dict(tf), ensure_ascii=False),
                )
            )
        if chunk_rows:
            await self._db.executemany(
                "INSERT INTO rag_chunks "
                "(project_id, chunk_id, path, line_start, line_end, content, kind, length, tf_blob) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                chunk_rows,
            )

        # Meta row: global IDF + tuning knobs. IDF is the only field we
        # pickle (a JSON map of ~50k tokens to floats is fine but pickle
        # is meaningfully smaller on large vocabularies).
        idf_blob = pickle.dumps(rag._idf, protocol=pickle.HIGHEST_PROTOCOL)
        await self._db.execute(
            "INSERT INTO rag_meta "
            "(project_id, schema_version, doc_count, avgdl, k1, b, "
            " max_chunk_lines, soft_chunk_lines, overlap_lines, idf_blob) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                project_id,
                SCHEMA_VERSION,
                len(rag.chunks),
                rag._avgdl,
                rag._k1,
                rag._b,
                rag.max_chunk_lines,
                rag.soft_chunk_lines,
                rag.overlap_lines,
                idf_blob,
            ),
        )
        await self._db.commit()

    async def load(self, project_id: str) -> SimpleRAG | None:
        """rehydrate a previously-saved RAG.

        Returns ``None`` if there's nothing saved for ``project_id`` or
        the saved schema version is older than the current code -- in
        which case the caller should rebuild from scratch and call
        :meth:`save` again.
        """
        if not self._db:
            return None
        cur = await self._db.execute(
            "SELECT schema_version, avgdl, k1, b, max_chunk_lines, "
            "soft_chunk_lines, overlap_lines, idf_blob "
            "FROM rag_meta WHERE project_id = ?",
            (project_id,),
        )
        meta = await cur.fetchone()
        if not meta:
            return None

        (
            schema_version, avgdl, k1, b,
            max_chunk_lines, soft_chunk_lines, overlap_lines, idf_blob,
        ) = meta
        if schema_version != SCHEMA_VERSION:
            # Stale layout; drop and force the caller to rebuild.
            await self.delete_project(project_id)
            return None

        rag = SimpleRAG(
            k1=k1, b=b,
            max_chunk_lines=max_chunk_lines,
            soft_chunk_lines=soft_chunk_lines,
            overlap_lines=overlap_lines,
        )
        rag._idf = pickle.loads(idf_blob)
        rag._avgdl = float(avgdl)

        # Chunks come back in chunk_id order so the in-memory list stays
        # aligned with the TF vector list (same invariant the in-memory
        # SimpleRAG relies on).
        cur = await self._db.execute(
            "SELECT chunk_id, path, line_start, line_end, content, kind, length, tf_blob "
            "FROM rag_chunks WHERE project_id = ? ORDER BY chunk_id",
            (project_id,),
        )
        chunks_rows = await cur.fetchall()
        file_chunks: dict[str, list[int]] = {}
        for idx, (_cid, path, line_start, line_end, content, kind, length, tf_blob) in enumerate(chunks_rows):
            rag.chunks.append(
                Chunk(
                    file_path=path,
                    line_start=line_start,
                    line_end=line_end,
                    content=content,
                    kind=kind,
                )
            )
            tf = Counter(json.loads(tf_blob))
            rag._tf_vectors.append(tf)
            rag._chunk_lens.append(length)
            file_chunks.setdefault(path, []).append(idx)

        rag._file_to_chunks = file_chunks

        cur = await self._db.execute(
            "SELECT path, sha FROM rag_files WHERE project_id = ?",
            (project_id,),
        )
        rag._file_sha = {row[0]: row[1] for row in await cur.fetchall()}

        return rag
