"""export wiki as a directory of Markdown files."""

from __future__ import annotations

from pathlib import Path

from repowiki.core.wiki_builder import Wiki


def export_markdown(wiki: Wiki, output_dir: str | Path) -> None:
    """write each wiki page as a .md file, plus a _sidebar.md for navigation."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # write each page
    for page in wiki.pages:
        page_path = out / f"{page.id}.md"
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(page.content, encoding="utf-8")

    # write sidebar navigation
    sidebar_lines = [f"# {wiki.project_name}\n"]
    for item in wiki.sidebar:
        if item.page_id:
            sidebar_lines.append(f"- [{item.title}]({item.page_id}.md)")
        else:
            sidebar_lines.append(f"- **{item.title}**")
        for child in item.children:
            sidebar_lines.append(f"  - [{child.title}]({child.page_id}.md)")

    sidebar_path = out / "_sidebar.md"
    sidebar_path.write_text("\n".join(sidebar_lines) + "\n", encoding="utf-8")
