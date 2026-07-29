"""Tests for the long-lived content-addressed LLM cache."""

from __future__ import annotations

import asyncio
import json
import time

from repowiki.core.cache import Cache, content_hash


def _run(coro):
    return asyncio.run(coro)


def _make_cache(tmp_path) -> Cache:
    c = Cache(db_path=tmp_path / "cache.db")
    asyncio.run(c.init())
    return c


def test_fresh_entry_survives_default_ttl(tmp_path):
    c = _make_cache(tmp_path)
    asyncio.run(c.put("k1", {"a": 1}))
    assert asyncio.run(c.get("k1")) == {"a": 1}
    asyncio.run(c.close())


def test_expired_entry_is_deleted(tmp_path):
    c = _make_cache(tmp_path)
    old = time.time() - 10 * 365 * 24 * 3600
    asyncio.run(c._db.execute(
        "INSERT INTO cache (key, value, created_at) VALUES (?, ?, ?)",
        ("k2", json.dumps({"b": 2}), old),
    ))
    asyncio.run(c._db.commit())
    assert asyncio.run(c.get("k2")) is None
    cursor = asyncio.run(c._db.execute("SELECT COUNT(*) FROM cache WHERE key = ?", ("k2",)))
    (n,) = asyncio.run(cursor.fetchone())
    assert n == 0
    asyncio.run(c.close())


def test_clear_wipes_results_but_keeps_projects(tmp_path):
    c = _make_cache(tmp_path)
    asyncio.run(c.put("k3", {"c": 3}))
    asyncio.run(c.put("k4", {"d": 4}))
    asyncio.run(c.save_project("p1", {"name": "demo"}))

    removed = asyncio.run(c.clear())

    assert removed == 2
    assert asyncio.run(c.get("k3")) is None
    assert asyncio.run(c.get("k4")) is None
    assert asyncio.run(c.load_project("p1")) == {"name": "demo"}
    asyncio.run(c.close())


class _StubLLM:
    def __init__(self):
        self.calls = 0

    async def complete(self, messages, max_tokens=4096):
        self.calls += 1
        return '{"name": "mod", "purpose": "test module", "files": []}'


def test_module_analysis_reuses_cache_on_second_run(tmp_path):
    from repowiki.core.analyzer import Analyzer
    from repowiki.core.models import FileInfo, ProjectContext

    c = _make_cache(tmp_path)
    llm = _StubLLM()
    analyzer = Analyzer(llm=llm, cache=c, language="en")
    files = [FileInfo(path="mod/a.py", size=10, language="python", content="x = 1\n")]
    project = ProjectContext(name="demo", root=str(tmp_path), files=files, file_tree="mod/a.py")

    doc1, cached1 = asyncio.run(analyzer._analyze_one_module("mod", files, "summary", project))
    doc2, cached2 = asyncio.run(analyzer._analyze_one_module("mod", files, "summary", project))

    assert cached1 is False
    assert cached2 is True
    assert llm.calls == 1
    assert doc1.name == doc2.name == "mod"
    asyncio.run(c.close())


def test_content_hash_is_stable_and_distinct():
    assert content_hash("abc") == content_hash("abc")
    assert content_hash("abc") != content_hash("abd")
