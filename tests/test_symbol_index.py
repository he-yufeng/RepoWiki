"""Symbol index: one page aggregating every key symbol, grouped by kind."""

from __future__ import annotations

import re

from repowiki.core.graph import DependencyGraph
from repowiki.core.models import (
    FileDoc,
    FileInfo,
    ModuleDoc,
    ProjectContext,
    ProjectOverview,
    Symbol,
    WikiData,
)
from repowiki.core.wiki_builder import Wiki, WikiBuilder
from repowiki.export.html import export_html
from repowiki.export.markdown import export_markdown


def _file(path: str, content: str = "") -> FileInfo:
    return FileInfo(
        path=path,
        size=len(content),
        language="python",
        lines=content.count("\n") + 1,
        preview=content,
        content=content,
    )


def _wiki_data() -> WikiData:
    # modules are listed beta-first and symbols out of name order on purpose,
    # so the tests only pass when the index sorts them deterministically
    return WikiData(
        overview=ProjectOverview(name="demo", one_liner="demo project"),
        modules=[
            ModuleDoc(
                name="beta",
                purpose="beta package",
                files=[
                    FileDoc(
                        path="beta/runner.py",
                        purpose="runs beta",
                        key_symbols=[
                            Symbol(name="shared_helper", kind="function"),
                            Symbol(name="run_beta", kind="function", description="entry point"),
                            Symbol(name="start", kind="method", description="boots the runner"),
                        ],
                    ),
                ],
            ),
            ModuleDoc(
                name="alpha",
                purpose="alpha package",
                files=[
                    FileDoc(
                        path="alpha/core.py",
                        purpose="core alpha pieces",
                        key_symbols=[
                            Symbol(name="shared_helper", kind="function"),
                            Symbol(name="AlphaEngine", kind="class", description="drives alpha"),
                            Symbol(name="VERSION", kind=""),
                        ],
                    ),
                ],
            ),
        ],
    )


def _build(wiki_data: WikiData | None = None) -> Wiki:
    files = [
        _file("alpha/core.py", "X = 1\n"),
        _file("beta/runner.py", "import alpha.core\n"),
    ]
    project = ProjectContext(
        name="demo",
        root="/tmp/demo",
        files=files,
        file_tree="\n".join(f.path for f in files),
    )
    graph = DependencyGraph.build_from_project(project)
    return WikiBuilder().build(project, wiki_data or _wiki_data(), graph)


def _index(wiki: Wiki) -> str:
    page = wiki.get_page("symbols")
    assert page is not None
    return page.content


def test_kind_sections_follow_first_appearance_order():
    content = _index(_build())
    heads = [content.index(f"## {kind}") for kind in ("Function", "Method", "Class", "Other")]
    assert heads == sorted(heads)


def test_modules_and_symbols_sorted_within_each_kind():
    content = _index(_build())
    assert content.index("### [alpha](modules/alpha.md)") < content.index(
        "### [beta](modules/beta.md)"
    )
    function = content[content.index("## Function"):content.index("## Method")]
    assert function.index("`run_beta`") < function.index("`shared_helper`](modules/beta.md)")


def test_entries_link_to_owning_module_and_keep_descriptions():
    content = _index(_build())
    assert "- [`AlphaEngine`](modules/alpha.md) - drives alpha" in content
    assert "- [`run_beta`](modules/beta.md) - entry point" in content
    assert "- [`start`](modules/beta.md) - boots the runner" in content


def test_symbol_without_description_gets_no_trailing_dash():
    content = _index(_build())
    assert "- [`shared_helper`](modules/alpha.md)\n" in content


def test_symbol_with_empty_kind_lands_in_other_section():
    content = _index(_build())
    other = content.split("## Other")[1]
    assert "- [`VERSION`](modules/alpha.md)" in other


def test_shared_symbol_listed_under_each_owning_module():
    content = _index(_build())
    assert "- [`shared_helper`](modules/alpha.md)" in content
    assert "- [`shared_helper`](modules/beta.md)" in content


def test_header_counts_symbols_and_modules():
    content = _index(_build())
    assert "6 symbols across 2 modules" in content


def test_sidebar_gets_symbol_index_entry_after_dependencies():
    wiki = _build()
    ids = [item.page_id for item in wiki.sidebar]
    assert ids[-1] == "symbols"
    assert ids[-2] == "dependencies"
    assert wiki.sidebar[-1].title == "Symbol Index"


def test_project_without_symbols_gets_no_index_page():
    # documented choice: a project with no documented symbols simply skips the
    # page instead of rendering an empty-state stub
    bare = WikiData(
        overview=ProjectOverview(name="demo"),
        modules=[
            ModuleDoc(name="alpha", files=[FileDoc(path="alpha/core.py")]),
        ],
    )
    wiki = _build(bare)
    assert wiki.get_page("symbols") is None
    assert all(item.page_id != "symbols" for item in wiki.sidebar)


def test_incremental_export_keeps_index_and_removes_it_when_symbols_go(tmp_path):
    # the index has no LLM cache key, so it rides on the content-hash
    # fallback: byte-identical content is kept, and the page is deleted
    # once no module documents symbols anymore
    wiki = _build()
    first = export_markdown(wiki, tmp_path, page_inputs={})
    assert "symbols" in first["written"]
    second = export_markdown(wiki, tmp_path, page_inputs={})
    assert "symbols" in second["kept"]

    bare = WikiData(
        overview=ProjectOverview(name="demo"),
        modules=[ModuleDoc(name="alpha", files=[FileDoc(path="alpha/core.py")])],
    )
    third = export_markdown(_build(bare), tmp_path, page_inputs={})
    assert "symbols" in third["removed"]
    assert not (tmp_path / "symbols.md").exists()


def test_markdown_export_links_resolve_and_sidebar_readme_list_index(tmp_path):
    wiki = _build()
    export_markdown(wiki, tmp_path)
    sidebar = (tmp_path / "_sidebar.md").read_text(encoding="utf-8")
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "[Symbol Index](symbols.md)" in sidebar
    assert "[Symbol Index](symbols.md)" in readme

    link_re = re.compile(r"\]\(([^)]+?\.md)\)")
    found = 0
    for md_file in sorted(tmp_path.rglob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        for target in link_re.findall(text):
            if "://" in target:
                continue
            resolved = (md_file.parent / target).resolve()
            assert resolved.exists(), f"{md_file.name}: broken link {target}"
            found += 1
    assert found > 0


def test_html_export_turns_index_links_into_show_page_calls(tmp_path):
    out = tmp_path / "wiki.html"
    export_html(_build(), out)
    text = out.read_text(encoding="utf-8")
    assert "showPage('symbols')\">Symbol Index" in text
    assert "onclick=\"showPage('modules/alpha')\"><code>AlphaEngine</code>" in text
    assert 'href="modules/alpha.md"' not in text
