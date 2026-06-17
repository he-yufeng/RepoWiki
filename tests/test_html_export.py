"""Tests for the self-contained HTML wiki export."""

from repowiki.core.wiki_builder import SidebarItem, Wiki, WikiPage
from repowiki.export.html import export_html


def _wiki(content: str) -> Wiki:
    return Wiki(
        project_name="DemoProj",
        pages=[WikiPage(id="index", title="Overview", content=content)],
        sidebar=[SidebarItem(title="Overview", page_id="index")],
    )


def test_html_export_writes_a_file_with_the_project_title(tmp_path):
    out = tmp_path / "wiki.html"
    export_html(_wiki("# Overview\n\nWhat it does."), out)
    text = out.read_text(encoding="utf-8")
    assert text.startswith("<!DOCTYPE html>")
    assert "DemoProj" in text
    assert '<div id="page-index"' in text


def test_html_export_wraps_bullet_list_in_ul(tmp_path):
    out = tmp_path / "wiki.html"
    export_html(_wiki("- first\n- second\n- third"), out)
    text = out.read_text(encoding="utf-8")
    assert "<ul>" in text and "</ul>" in text
    assert text.count("<li>") == 3
    # the <ul> opens before the first <li> and closes after the last
    assert text.index("<ul>") < text.index("<li>") < text.index("</ul>")


def test_html_export_wraps_ordered_list_in_ol(tmp_path):
    out = tmp_path / "wiki.html"
    export_html(_wiki("1. read this\n2. then this\n3. finally this"), out)
    text = out.read_text(encoding="utf-8")
    assert "<ol>" in text and "</ol>" in text
    assert text.count("<li>") == 3
    assert text.index("<ol>") < text.index("<li>") < text.index("</ol>")


def test_html_export_closes_list_before_following_paragraph(tmp_path):
    out = tmp_path / "wiki.html"
    export_html(_wiki("- a bullet\nA following paragraph."), out)
    text = out.read_text(encoding="utf-8")
    # the list must close before the paragraph, not swallow it
    assert "</ul>" in text
    assert text.index("</ul>") < text.index("<p>A following paragraph.</p>")


def test_html_export_keeps_ordered_and_unordered_lists_separate(tmp_path):
    out = tmp_path / "wiki.html"
    export_html(_wiki("- bullet one\n- bullet two\n\n1. step one\n2. step two"), out)
    text = out.read_text(encoding="utf-8")
    assert "<ul>" in text and "<ol>" in text
    # the bullet list closes before the ordered list opens
    assert text.index("</ul>") < text.index("<ol>")
