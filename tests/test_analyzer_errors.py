"""LLM errors should surface via analyzer.errors instead of crashing."""
from __future__ import annotations

import pytest

from repowiki.core.analyzer import Analyzer
from repowiki.core.cache import Cache
from repowiki.core.models import FileInfo, ProjectContext
from repowiki.llm.client import LLMError


class _FailingLLM:
    """LLMClient stand-in that always raises LLMError."""

    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

    async def complete(self, messages, **_kwargs):
        raise LLMError("rate_limit_error: simulated")


def _tiny_project() -> ProjectContext:
    files = [
        FileInfo(
            path="src/foo.py",
            size=12,
            language="python",
            lines=2,
            preview="def foo():\n    return 1\n",
            content="def foo():\n    return 1\n",
            is_entrypoint=True,
        ),
    ]
    return ProjectContext(name="tiny", root="/tmp/tiny", files=files, file_tree="src/\n  foo.py")


@pytest.mark.asyncio
async def test_llm_failures_surface_in_errors_list(tmp_path):
    cache = Cache(db_path=tmp_path / "cache.db")
    await cache.init()

    analyzer = Analyzer(llm=_FailingLLM(), cache=cache, language="en", concurrency=1)
    progress_log: list[str] = []
    wiki_data = await analyzer.analyze(_tiny_project(), on_progress=progress_log.append)

    # pipeline must finish, not raise
    assert wiki_data is not None
    # at least overview / module / arch / guide all failed -> 4 errors
    assert len(analyzer.errors) >= 3
    # progress log got the [error] markers
    assert any("[error]" in line for line in progress_log)
    # placeholders are returned, not None
    assert wiki_data.overview is not None
    assert wiki_data.modules  # at least the failed module placeholder

    await cache.close()


@pytest.mark.asyncio
async def test_llm_client_raises_on_failure(monkeypatch):
    """LLMClient.complete must raise LLMError, not return error string."""
    from repowiki.llm import client as client_mod

    async def boom(**_kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(client_mod.litellm, "acompletion", boom)
    llm = client_mod.LLMClient(model="any", api_key="x")

    with pytest.raises(LLMError) as exc_info:
        await llm.complete([{"role": "user", "content": "hi"}])
    assert "network down" in str(exc_info.value)
    assert isinstance(exc_info.value.cause, RuntimeError)
