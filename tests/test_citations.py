"""Module pages should render `path:line` citations for each key symbol."""
from __future__ import annotations

from repowiki.core.graph import DependencyGraph
from repowiki.core.models import (
    FileDoc,
    ModuleDoc,
    ProjectContext,
    Symbol,
    WikiData,
)
from repowiki.core.wiki_builder import WikiBuilder
from repowiki.llm.prompts import build_module_prompt


def test_module_prompt_requests_line_field():
    msgs = build_module_prompt("core", "files", "test project", "en")
    user_text = msgs[1]["content"]
    assert '"line"' in user_text
    assert "REQUIRED" in user_text


def test_builder_renders_path_line_citation():
    module = ModuleDoc(
        name="core",
        purpose="x",
        files=[
            FileDoc(
                path="src/foo.py",
                purpose="does foo",
                key_symbols=[
                    Symbol(name="parse", kind="function", line=42, description="parses input"),
                    Symbol(name="Foo", kind="class", line=10),
                    Symbol(name="OPAQUE", kind="constant", line=0),  # 0 = unknown
                ],
            ),
        ],
    )
    project = ProjectContext(name="x", root="/tmp/x")
    wiki_data = WikiData(modules=[module])
    graph = DependencyGraph()  # empty graph, no edges
    wiki = WikiBuilder().build(project, wiki_data, graph)

    page = next(p for p in wiki.pages if p.id == "modules/core")
    # symbols with line should show src/foo.py:42
    assert "`src/foo.py:42`" in page.content
    assert "`src/foo.py:10`" in page.content
    # line=0 means unknown -> should NOT render a fake :0 citation
    assert "src/foo.py:0" not in page.content
    # but the symbol itself still appears
    assert "`OPAQUE`" in page.content
