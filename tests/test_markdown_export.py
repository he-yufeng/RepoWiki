"""Tests for the Markdown wiki export, including the README.md landing page."""

from repowiki.core.wiki_builder import SidebarItem, Wiki, WikiPage
from repowiki.export.markdown import export_markdown


def _wiki() -> Wiki:
    return Wiki(
        project_name="DemoProj",
        pages=[
            WikiPage(id="index", title="Overview", content="# Overview\n\nWhat it does."),
            WikiPage(id="architecture", title="Architecture", content="# Architecture\n"),
        ],
        sidebar=[
            SidebarItem(title="Overview", page_id="index"),
            SidebarItem(title="Architecture", page_id="architecture"),
        ],
    )


def test_writes_each_page_and_sidebar(tmp_path):
    export_markdown(_wiki(), tmp_path)
    assert (tmp_path / "index.md").read_text(encoding="utf-8").startswith("# Overview")
    assert (tmp_path / "architecture.md").exists()
    sidebar = (tmp_path / "_sidebar.md").read_text(encoding="utf-8")
    assert "[Architecture](architecture.md)" in sidebar


def test_writes_readme_landing_page_with_overview_and_contents(tmp_path):
    export_markdown(_wiki(), tmp_path)
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("# DemoProj")
    assert "What it does." in readme  # overview content is inlined
    assert "## Contents" in readme
    assert "[Overview](index.md)" in readme
    assert "[Architecture](architecture.md)" in readme


def test_readme_without_overview_still_lists_contents(tmp_path):
    wiki = Wiki(
        project_name="NoOverview",
        pages=[WikiPage(id="architecture", title="Architecture", content="# Architecture\n")],
        sidebar=[SidebarItem(title="Architecture", page_id="architecture")],
    )
    export_markdown(wiki, tmp_path)
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("# NoOverview")
    assert "## Contents" in readme
    assert "[Architecture](architecture.md)" in readme


def test_readme_includes_nested_children(tmp_path):
    wiki = Wiki(
        project_name="Nested",
        pages=[WikiPage(id="mod_a", title="Module A", content="# A\n")],
        sidebar=[
            SidebarItem(
                title="Modules",
                page_id="",
                children=[SidebarItem(title="Module A", page_id="mod_a")],
            )
        ],
    )
    export_markdown(wiki, tmp_path)
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "- **Modules**" in readme
    assert "  - [Module A](mod_a.md)" in readme
