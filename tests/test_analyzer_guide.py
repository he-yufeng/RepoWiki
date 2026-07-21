"""The reading guide must rank files by PageRank, not scan order."""

from __future__ import annotations

import asyncio
import json

from repowiki.core.analyzer import Analyzer
from repowiki.core.cache import Cache
from repowiki.core.models import FileInfo, ModuleDoc, ProjectContext

PAYLOAD = json.dumps({"introduction": "read in order", "steps": [], "tips": []})


class StubLLM:
    """records calls and returns canned JSON."""

    def __init__(self, payload: str = PAYLOAD):
        self.payload = payload
        self.calls: list[list[dict]] = []

    async def complete(self, messages, max_tokens=4096):
        self.calls.append(messages)
        return self.payload


def _file(path: str, content: str, *, is_config: bool = False) -> FileInfo:
    return FileInfo(
        path=path,
        size=len(content),
        language="python" if path.endswith(".py") else "markdown",
        lines=content.count("\n") + 1,
        preview=content,
        content=content,
        is_config=is_config,
    )


def _project(files: list[FileInfo]) -> ProjectContext:
    return ProjectContext(
        name="demo",
        root="/tmp/demo",
        files=files,
        file_tree="\n".join(f.path for f in files),
    )


def _rankings_block(messages: list[dict]) -> str:
    return messages[1]["content"].split("## Module Summaries")[0]


def _run(coro):
    return asyncio.run(coro)


def test_reading_guide_ranks_by_pagerank_not_scan_order(tmp_path):
    async def go():
        cache = Cache(db_path=tmp_path / "c.db")
        await cache.init()
        try:
            llm = StubLLM()
            analyzer = Analyzer(llm=llm, cache=cache)
            guide = await analyzer._generate_reading_guide(
                _project(
                    [
                        _file("README.md", "# demo\n", is_config=True),
                        _file("a.py", "import hub\n"),
                        _file("b.py", "import hub\n"),
                        _file("c.py", "import hub\n"),
                        _file("hub.py", "X = 1\n"),
                    ]
                ),
                [ModuleDoc(name="root", purpose="everything")],
                "tree",
            )
            return guide, llm
        finally:
            await cache.close()

    guide, llm = _run(go())

    # scan order puts README.md first, but every module imports hub.py,
    # so PageRank must lead the rankings with hub.py instead
    assert len(llm.calls) == 1
    rankings = _rankings_block(llm.calls[0])
    assert rankings.splitlines()[1].startswith("1. hub.py")
    assert guide.introduction == "read in order"


def test_reading_guide_cache_follows_ranking_inputs(tmp_path):
    async def go():
        cache = Cache(db_path=tmp_path / "c.db")
        await cache.init()
        try:
            llm = StubLLM()
            analyzer = Analyzer(llm=llm, cache=cache)
            docs = [ModuleDoc(name="root", purpose="everything")]
            v1 = _project(
                [
                    _file("README.md", "# demo\n", is_config=True),
                    _file("a.py", "import hub\n"),
                    _file("b.py", "import hub\n"),
                    _file("hub.py", "X = 1\n"),
                ]
            )
            await analyzer._generate_reading_guide(v1, docs, "tree")
            # identical inputs are served from cache
            await analyzer._generate_reading_guide(v1, docs, "tree")
            assert len(llm.calls) == 1

            # import-only edit: hub loses all inbound edges, so the ranking
            # (and therefore the cache key) must change even though the file
            # tree and module summaries are identical
            v2 = _project(
                [
                    _file("README.md", "# demo\n", is_config=True),
                    _file("a.py", "X = 1\n"),
                    _file("b.py", "import a\n"),
                    _file("hub.py", "import a\n"),
                ]
            )
            await analyzer._generate_reading_guide(v2, docs, "tree")
            assert len(llm.calls) == 2
            assert _rankings_block(llm.calls[1]).splitlines()[1].startswith("1. a.py")

            # v1 again hits its own cache entry
            await analyzer._generate_reading_guide(v1, docs, "tree")
            assert len(llm.calls) == 2
        finally:
            await cache.close()

    _run(go())


def test_reading_guide_falls_back_to_scan_order_without_imports(tmp_path):
    async def go():
        cache = Cache(db_path=tmp_path / "c.db")
        await cache.init()
        try:
            llm = StubLLM()
            analyzer = Analyzer(llm=llm, cache=cache)
            await analyzer._generate_reading_guide(
                _project(
                    [
                        _file("README.md", "# x\n", is_config=True),
                        _file("solo.py", "print(1)\n"),
                    ]
                ),
                [ModuleDoc(name="root", purpose="x")],
                "tree",
            )
            return llm
        finally:
            await cache.close()

    llm = _run(go())
    rankings = _rankings_block(llm.calls[0])
    assert "README.md" in rankings
    assert "solo.py" in rankings
