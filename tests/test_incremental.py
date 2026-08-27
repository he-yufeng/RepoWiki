"""Incremental re-generation: unchanged pages skip both the LLM and the rewrite."""

from __future__ import annotations

import asyncio
import json
import re

from repowiki.core.analyzer import Analyzer
from repowiki.core.cache import Cache
from repowiki.core.graph import DependencyGraph
from repowiki.core.models import FileInfo, ProjectContext
from repowiki.core.state import STATE_FILENAME
from repowiki.core.wiki_builder import WikiBuilder
from repowiki.export.markdown import export_markdown

ALL_PAGES = ["architecture", "dependencies", "index", "modules/a", "modules/b", "reading-guide"]


class StubLLM:
    """hands out canned JSON per pipeline stage and records what was asked."""

    def __init__(self):
        self.model = "stub-model"
        self.calls: list[str] = []

    async def complete(self, messages, max_tokens=4096):
        user = messages[-1]["content"]
        if "Generate a project overview" in user:
            self.calls.append("overview")
            return json.dumps({"name": "demo", "one_liner": "demo project", "description": "d"})
        if "Analyze the architecture" in user:
            self.calls.append("arch")
            return json.dumps({"architecture_type": "library", "description": "a"})
        if "Create a reading guide" in user:
            self.calls.append("guide")
            return json.dumps(
                {"introduction": "i", "steps": [{"order": 1, "title": "start"}], "tips": []}
            )
        m = re.search(r"Document the '([^']+)' module", user)
        if m:
            self.calls.append(f"module:{m.group(1)}")
            return json.dumps(
                {"name": m.group(1), "purpose": f"{m.group(1)} does things", "files": []}
            )
        raise AssertionError(f"unexpected prompt: {user[:80]}")


def _file(path: str, content: str) -> FileInfo:
    return FileInfo(
        path=path,
        size=len(content),
        language="python",
        lines=content.count("\n") + 1,
        preview=content,
        content=content,
    )


def _project(files: list[FileInfo]) -> ProjectContext:
    return ProjectContext(
        name="demo",
        root="/tmp/demo",
        files=files,
        file_tree="\n".join(f.path for f in files),
    )


FILES_V1 = [
    _file("a/one.py", "import b.two\nX = 1\n"),
    _file("a/three.py", "import a.one\nY = 3\n"),
    _file("b/two.py", "Z = 2\n"),
]


def _run_pipeline(project, out_dir, cache_path, llm, *, full=False, model="stub-model"):
    llm.model = model

    async def go():
        cache = Cache(db_path=cache_path)
        await cache.init()
        try:
            analyzer = Analyzer(llm=llm, cache=cache, language="en")
            wiki_data = await analyzer.analyze(project)
            return wiki_data, dict(analyzer.cache_keys)
        finally:
            await cache.close()

    wiki_data, cache_keys = asyncio.run(go())
    graph = DependencyGraph.build_from_project(project)
    wiki = WikiBuilder().build(project, wiki_data, graph)
    return export_markdown(
        wiki, out_dir, page_inputs=cache_keys, model=model, language="en", full=full
    )


def _snapshot(out_dir):
    return {
        str(p.relative_to(out_dir)): p.read_bytes()
        for p in sorted(out_dir.rglob("*"))
        if p.is_file()
    }


def _mtimes(out_dir):
    return {
        str(p.relative_to(out_dir)): p.stat().st_mtime_ns
        for p in sorted(out_dir.rglob("*"))
        if p.is_file()
    }


def _read_state(out_dir):
    return json.loads((out_dir / STATE_FILENAME).read_text(encoding="utf-8"))


def test_first_run_writes_all_pages_and_state(tmp_path):
    out = tmp_path / "wiki"
    llm = StubLLM()
    summary = _run_pipeline(_project(FILES_V1), out, tmp_path / "cache.db", llm)

    for page_id in ALL_PAGES:
        assert (out / f"{page_id}.md").exists(), page_id
    assert (out / "_sidebar.md").exists()
    assert (out / "README.md").exists()

    state = _read_state(out)
    assert state["version"] == 1
    assert state["model"] == "stub-model"
    assert state["language"] == "en"
    assert sorted(state["pages"]) == ALL_PAGES

    assert sorted(summary["written"]) == ALL_PAGES
    assert summary["kept"] == [] and summary["removed"] == []
    assert sorted(llm.calls) == ["arch", "guide", "module:a", "module:b", "overview"]


def test_second_run_with_no_changes_skips_everything(tmp_path):
    out = tmp_path / "wiki"
    llm = StubLLM()
    _run_pipeline(_project(FILES_V1), out, tmp_path / "cache.db", llm)
    calls_after_first = len(llm.calls)
    bytes_before = _snapshot(out)
    mtimes_before = _mtimes(out)

    summary = _run_pipeline(_project(FILES_V1), out, tmp_path / "cache.db", llm)

    assert summary["written"] == [] and summary["removed"] == []
    assert sorted(summary["kept"]) == ALL_PAGES
    assert len(llm.calls) == calls_after_first
    # an unchanged run touches nothing on disk, not even the state file
    assert _snapshot(out) == bytes_before
    assert _mtimes(out) == mtimes_before


def test_single_file_change_regenerates_only_its_module_page(tmp_path):
    out = tmp_path / "wiki"
    llm = StubLLM()
    _run_pipeline(_project(FILES_V1), out, tmp_path / "cache.db", llm)
    calls_after_first = len(llm.calls)
    module_a_before = (out / "modules/a.md").read_bytes()
    mtimes_before = _mtimes(out)

    changed = [
        _file("a/one.py", "import b.two\nX = 1\n"),
        _file("a/three.py", "import a.one\nY = 3\n"),
        _file("b/two.py", "Z = 22\n"),
    ]
    summary = _run_pipeline(_project(changed), out, tmp_path / "cache.db", llm)

    assert summary["written"] == ["modules/b"]
    assert sorted(summary["kept"]) == [
        "architecture",
        "dependencies",
        "index",
        "modules/a",
        "reading-guide",
    ]
    assert llm.calls[calls_after_first:] == ["module:b"]
    assert (out / "modules/a.md").read_bytes() == module_a_before
    assert _mtimes(out)["modules/a.md"] == mtimes_before["modules/a.md"]


def test_full_flag_rewrites_everything(tmp_path):
    out = tmp_path / "wiki"
    llm = StubLLM()
    _run_pipeline(_project(FILES_V1), out, tmp_path / "cache.db", llm)
    calls_after_first = len(llm.calls)

    summary = _run_pipeline(_project(FILES_V1), out, tmp_path / "cache.db", llm, full=True)

    assert sorted(summary["written"]) == ALL_PAGES
    assert summary["kept"] == [] and summary["removed"] == []
    # page writes are forced, but the content-addressed analysis cache still
    # holds, so a --full re-run stays free of LLM calls
    assert len(llm.calls) == calls_after_first


def test_corrupt_state_file_falls_back_to_full_regeneration(tmp_path):
    out = tmp_path / "wiki"
    llm = StubLLM()
    _run_pipeline(_project(FILES_V1), out, tmp_path / "cache.db", llm)

    (out / STATE_FILENAME).write_text("{ not json", encoding="utf-8")
    summary = _run_pipeline(_project(FILES_V1), out, tmp_path / "cache.db", llm)

    assert sorted(summary["written"]) == ALL_PAGES
    assert sorted(_read_state(out)["pages"]) == ALL_PAGES


def test_removed_module_page_is_deleted(tmp_path):
    out = tmp_path / "wiki"
    llm = StubLLM()
    _run_pipeline(_project(FILES_V1), out, tmp_path / "cache.db", llm)

    only_a = [
        _file("a/one.py", "import b.two\nX = 1\n"),
        _file("a/three.py", "import a.one\nY = 3\n"),
    ]
    summary = _run_pipeline(_project(only_a), out, tmp_path / "cache.db", llm)

    # without the cross-module import target the dependencies page goes too
    assert sorted(summary["removed"]) == ["dependencies", "modules/b"]
    assert summary["kept"] == ["modules/a"]
    assert sorted(summary["written"]) == ["architecture", "index", "reading-guide"]
    assert not (out / "modules/b.md").exists()
    assert not (out / "dependencies.md").exists()

    state = _read_state(out)
    assert "modules/b" not in state["pages"]
    assert "dependencies" not in state["pages"]
    assert "modules/b.md" not in (out / "_sidebar.md").read_text(encoding="utf-8")


def test_model_change_invalidates_llm_pages(tmp_path):
    out = tmp_path / "wiki"
    llm = StubLLM()
    _run_pipeline(_project(FILES_V1), out, tmp_path / "cache.db", llm)
    calls_after_first = len(llm.calls)

    summary = _run_pipeline(
        _project(FILES_V1), out, tmp_path / "cache.db", llm, model="other-model"
    )

    # the graph-only dependencies page has no model inputs, so it survives
    assert sorted(summary["written"]) == [
        "architecture",
        "index",
        "modules/a",
        "modules/b",
        "reading-guide",
    ]
    assert summary["kept"] == ["dependencies"]
    assert sorted(llm.calls[calls_after_first:]) == [
        "arch",
        "guide",
        "module:a",
        "module:b",
        "overview",
    ]
    assert _read_state(out)["model"] == "other-model"
