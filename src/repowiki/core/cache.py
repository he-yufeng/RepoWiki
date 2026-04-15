"""sqlite-based cache for analysis results."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import aiosqlite

_CACHE_DIR = Path.home() / ".repowiki"
_CACHE_DB = _CACHE_DIR / "cache.db"
_DEFAULT_TTL = 7 * 24 * 3600  # 7 days


def content_hash(content: str) -> str:
    """sha256 hash truncated to 24 chars, used as cache key."""
    return hashlib.sha256(content.encode()).hexdigest()[:24]


class Cache:
    """async SQLite cache for LLM analysis results."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path or _CACHE_DB)
        self._db: aiosqlite.Connection | None = None

    async def init(self):
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.execute(
            "CREATE TABLE IF NOT EXISTS cache "
            "(key TEXT PRIMARY KEY, value TEXT, created_at REAL)"
        )
        await self._db.execute(
            "CREATE TABLE IF NOT EXISTS projects "
            "(id TEXT PRIMARY KEY, data TEXT, created_at REAL)"
        )
        await self._db.commit()

    async def get(self, key: str, ttl: int = _DEFAULT_TTL) -> dict | list | None:
        if not self._db:
            return None
        cursor = await self._db.execute(
            "SELECT value, created_at FROM cache WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        value, created_at = row
        if time.time() - created_at > ttl:
            await self._db.execute("DELETE FROM cache WHERE key = ?", (key,))
            await self._db.commit()
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    async def put(self, key: str, value: dict | list) -> None:
        if not self._db:
            return
        await self._db.execute(
            "INSERT OR REPLACE INTO cache (key, value, created_at) VALUES (?, ?, ?)",
            (key, json.dumps(value, ensure_ascii=False), time.time()),
        )
        await self._db.commit()

    async def save_project(self, project_id: str, data: dict) -> None:
        if not self._db:
            return
        await self._db.execute(
            "INSERT OR REPLACE INTO projects (id, data, created_at) VALUES (?, ?, ?)",
            (project_id, json.dumps(data, ensure_ascii=False), time.time()),
        )
        await self._db.commit()

    async def load_project(self, project_id: str) -> dict | None:
        if not self._db:
            return None
        cursor = await self._db.execute(
            "SELECT data FROM projects WHERE id = ?", (project_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return None

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None
