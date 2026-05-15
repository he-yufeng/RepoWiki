"""Token budget controls how much project context the analyzer ships."""
from __future__ import annotations

from repowiki.core.analyzer import Analyzer, _approx_tokens
from repowiki.core.models import FileInfo, ProjectContext


def _file(path: str, body: str, *, cfg=False, entry=False) -> FileInfo:
    return FileInfo(
        path=path,
        size=len(body.encode()),
        language="python",
        lines=body.count("\n") + 1,
        preview=body,
        content=body,
        is_config=cfg,
        is_entrypoint=entry,
    )


def _bigfile(path: str, n_chars: int, **kw) -> FileInfo:
    # mix words so tiktoken doesn't BPE-collapse a single repeated char
    body = ("def fn(a, b): return a + b  # words and tokens here\n" * (n_chars // 50))
    return _file(path, body[:n_chars], **kw)


def test_approx_tokens_estimate_for_short_text():
    assert _approx_tokens("hello world") <= 5


def test_unlimited_budget_includes_everything():
    files = [
        _bigfile("a.py", 4000, cfg=True),
        _bigfile("b.py", 4000, cfg=True),
        _bigfile("c.py", 4000, cfg=True),
    ]
    project = ProjectContext(name="x", root="/tmp/x", files=files, file_tree="")
    analyzer = Analyzer(llm=None, cache=None, max_context_tokens=0)  # 0 = unlimited

    ctx = analyzer._build_key_files_context(project)
    assert "a.py" in ctx and "b.py" in ctx and "c.py" in ctx


def test_tight_budget_drops_lowest_priority_files():
    files = [
        _bigfile("important.py", 3000, cfg=True),
        _bigfile("other.py", 3000, cfg=True),
        _bigfile("third.py", 3000, cfg=True),
    ]
    project = ProjectContext(name="x", root="/tmp/x", files=files, file_tree="")
    # budget that fits ~one file's body but not all three
    analyzer = Analyzer(llm=None, cache=None, max_context_tokens=1200)

    ctx = analyzer._build_key_files_context(project)
    # something must be dropped
    assert ctx.count("```") < 6  # 6 = three files * 2 fence pairs
    # at least one file got included
    assert "```" in ctx


def test_dropped_files_still_get_skipped_stub():
    files = [_bigfile(f"f{i}.py", 3000, cfg=True) for i in range(5)]
    project = ProjectContext(name="x", root="/tmp/x", files=files, file_tree="")
    analyzer = Analyzer(llm=None, cache=None, max_context_tokens=1500)

    ctx = analyzer._build_key_files_context(project)
    assert "skipped to fit context budget" in ctx


def test_config_files_prioritised_over_entrypoints():
    files = [
        _file("main.py", "print('hi')\n", entry=True),
        _file("pyproject.toml", "[project]\nname='x'\n", cfg=True),
    ]
    project = ProjectContext(name="x", root="/tmp/x", files=files, file_tree="")
    analyzer = Analyzer(llm=None, cache=None, max_context_tokens=0)

    ctx = analyzer._build_key_files_context(project)
    # config should appear before entrypoint in the rendered context
    assert ctx.index("pyproject.toml") < ctx.index("main.py")
