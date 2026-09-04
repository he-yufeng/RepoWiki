"""Cross-reference links: backticked symbol/file mentions become page links."""

from __future__ import annotations

import re

from repowiki.core.graph import DependencyGraph
from repowiki.core.models import (
    FileDoc,
    FileInfo,
    ModuleDoc,
    ProjectContext,
    ProjectOverview,
    ReadingGuide,
    ReadingStep,
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
    return WikiData(
        overview=ProjectOverview(
            name="demo",
            one_liner="demo project",
            key_features=["built around `shared_helper`"],
        ),
        modules=[
            ModuleDoc(
                name="alpha",
                purpose="alpha package",
                files=[
                    FileDoc(
                        path="alpha/core.py",
                        purpose="core alpha pieces",
                        key_symbols=[
                            Symbol(name="AlphaEngine", kind="class", description="drives alpha"),
                            Symbol(name="shared_helper", kind="function"),
                        ],
                    ),
                ],
            ),
            ModuleDoc(
                name="beta",
                purpose="beta package",
                description=(
                    "delegates to `AlphaEngine` for the heavy lifting.\n\n"
                    "```python\nengine = `AlphaEngine`()\n```"
                ),
                files=[
                    FileDoc(
                        path="beta/runner.py",
                        purpose="runs beta",
                        key_symbols=[
                            Symbol(name="run_beta", kind="function"),
                            Symbol(name="shared_helper", kind="function"),
                        ],
                    ),
                ],
            ),
        ],
        reading_guide=ReadingGuide(
            steps=[
                ReadingStep(
                    order=1,
                    title="start",
                    files=["alpha/core.py"],
                    explanation="read `AlphaEngine` first",
                )
            ],
        ),
    )


def _build() -> Wiki:
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
    return WikiBuilder().build(project, _wiki_data(), graph)


def test_known_symbol_mention_becomes_a_link():
    beta = _build().get_page("modules/beta")
    assert "[`AlphaEngine`](alpha.md)" in beta.content


def test_fenced_code_mention_stays_plain():
    beta = _build().get_page("modules/beta")
    assert "engine = `AlphaEngine`()" in beta.content
    # only the prose mention is linked, not the fenced one
    assert beta.content.count("[`AlphaEngine`](alpha.md)") == 1


def test_file_path_mentions_become_links():
    wiki = _build()
    guide = wiki.get_page("reading-guide")
    assert "[`alpha/core.py`](modules/alpha.md)" in guide.content
    dep = wiki.get_page("dependencies")
    assert "[`alpha/core.py`](modules/alpha.md)" in dep.content
    assert "[`beta/runner.py`](modules/beta.md)" in dep.content


def test_owning_page_does_not_link_to_itself():
    alpha = _build().get_page("modules/alpha")
    assert "[`alpha/core.py`]" not in alpha.content
    assert "[`AlphaEngine`]" not in alpha.content
    assert "`AlphaEngine`" in alpha.content  # still plain inline code


def test_first_seen_page_wins_for_shared_symbols():
    index = _build().get_page("index")
    assert "[`shared_helper`](modules/alpha.md)" in index.content


def test_every_emitted_relative_link_resolves(tmp_path):
    wiki = _build()
    export_markdown(wiki, tmp_path)
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


def test_html_export_turns_page_links_into_show_page_calls(tmp_path):
    out = tmp_path / "wiki.html"
    export_html(_build(), out)
    text = out.read_text(encoding="utf-8")
    assert "onclick=\"showPage('modules/alpha')\"><code>AlphaEngine</code>" in text
    assert 'href="alpha.md"' not in text
    assert 'href="modules/alpha.md"' not in text
