"""verify the module-analysis semaphore now serializes only LLM calls.

Before the fix, the semaphore wrapped the entire ``_analyze_one_module``
method, including non-async setup. After the fix, only the
``llm.complete()`` call sits inside ``async with self._sem:``.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from repowiki.core.analyzer import Analyzer
from repowiki.core.models import FileInfo, ProjectContext


class _FakeLLM:
    """async LLM stub that sleeps to simulate provider latency."""

    def __init__(self, delay: float = 0.3):
        self.delay = delay
        self.calls = 0
        self.model = "fake"

    async def complete(self, messages, **kwargs):
        self.calls += 1
        await asyncio.sleep(self.delay)
        # minimal valid module JSON so the parser is happy
        return '{"name": "m", "purpose": "p", "files": []}'

    async def stream(self, messages, **kwargs):
        if False:
            yield ""


class _FakeCache:
    async def init(self):
        pass

    async def get(self, key, ttl=None):
        return None

    async def put(self, key, value):
        pass

    async def close(self):
        pass


def _make_project(n_modules: int = 5) -> ProjectContext:
    files = []
    for i in range(n_modules):
        files.append(
            FileInfo(
                path=f"mod{i}/a.py",
                size=10,
                language="python",
                lines=2,
                content="def f():\n    pass\n",
            )
        )
    return ProjectContext(
        name="p",
        root=".",
        files=files,
        file_tree="\n".join(f.path for f in files),
    )


@pytest.mark.asyncio
async def test_modules_run_concurrently():
    project = _make_project(n_modules=5)
    llm = _FakeLLM(delay=0.3)
    cache = _FakeCache()
    analyzer = Analyzer(llm=llm, cache=cache, concurrency=5)

    start = time.monotonic()
    modules = analyzer._group_into_modules(project.files)
    docs = await analyzer._analyze_modules(modules, "summary", project, lambda _m: None)
    elapsed = time.monotonic() - start

    # 5 modules * 0.3s = 1.5s serial, ~0.3s parallel. Allow generous slack.
    assert llm.calls == 5
    assert len(docs) == 5
    assert elapsed < 0.9, f"modules did not run in parallel (took {elapsed:.2f}s)"


def test_build_module_context_is_deterministic_and_independent():
    """_build_module_context now runs in a thread pool; verify it's a pure
    function (no shared mutable state) so executor parallelism is safe."""
    files_a = [
        FileInfo(path="m/a.py", size=10, language="python", lines=2,
                 content="def f():\n    pass\n"),
    ]
    files_b = [
        FileInfo(path="m/b.py", size=10, language="python", lines=2,
                 content="def g():\n    pass\n"),
    ]
    ctx_a1 = Analyzer._build_module_context("m_a", files_a)
    ctx_a2 = Analyzer._build_module_context("m_a", files_a)
    ctx_b = Analyzer._build_module_context("m_b", files_b)

    # Same inputs -> identical cache key + body
    assert ctx_a1 == ctx_a2
    # Different inputs -> different cache key
    assert ctx_a1[1] != ctx_b[1]
    # Cache key includes the module name and a content hash suffix
    assert ctx_a1[1].startswith("module:m_a:")
    # Body carries the file path and language fence
    assert "m/a.py" in ctx_a1[0] and "```python" in ctx_a1[0]
