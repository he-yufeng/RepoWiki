"""export wiki as a directory of Markdown files."""

from __future__ import annotations

from pathlib import Path

from repowiki.core.cache import content_hash
from repowiki.core.state import STATE_VERSION, load_state, save_state
from repowiki.core.wiki_builder import Wiki


def export_markdown(
    wiki: Wiki,
    output_dir: str | Path,
    *,
    page_inputs: dict[str, str] | None = None,
    model: str = "",
    language: str = "",
    full: bool = False,
) -> dict[str, list[str]] | None:
    """write each wiki page as a .md file, plus a _sidebar.md for navigation.

    With page_inputs (page id -> fingerprint of what generated the page), the
    export runs incrementally: pages whose fingerprint still matches the state
    file are left untouched, pages for removed modules are deleted, and the
    state file is refreshed. full=True ignores the state file and rewrites
    everything. Returns a written/kept/removed summary in incremental mode.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    incremental = page_inputs is not None
    state = load_state(out) if incremental and not full else None
    old_pages: dict = state["pages"] if state else {}

    written: list[str] = []
    kept: list[str] = []
    removed: list[str] = []
    new_pages: dict[str, dict] = {}

    # write each page
    for page in wiki.pages:
        page_path = out / f"{page.id}.md"
        if incremental:
            fingerprint = page_inputs.get(page.id) or f"page:{content_hash(page.content)}"
            new_pages[page.id] = {"inputs": fingerprint}
            if old_pages.get(page.id, {}).get("inputs") == fingerprint and page_path.exists():
                kept.append(page.id)
                continue
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(page.content, encoding="utf-8")
        written.append(page.id)

    if incremental:
        for old_id in old_pages:
            if old_id not in new_pages:
                stale = out / f"{old_id}.md"
                if stale.exists():
                    stale.unlink()
                removed.append(old_id)

    _write_if_changed(out / "_sidebar.md", _sidebar_text(wiki))
    _write_if_changed(out / "README.md", _readme_text(wiki))

    if incremental:
        new_state = {
            "version": STATE_VERSION,
            "model": model,
            "language": language,
            "pages": new_pages,
        }
        if new_state != state:
            save_state(out, new_state)
        return {"written": written, "kept": kept, "removed": removed}
    return None


def _write_if_changed(path: Path, content: str) -> None:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def _sidebar_text(wiki: Wiki) -> str:
    sidebar_lines = [f"# {wiki.project_name}\n"]
    for item in wiki.sidebar:
        if item.page_id:
            sidebar_lines.append(f"- [{item.title}]({item.page_id}.md)")
        else:
            sidebar_lines.append(f"- **{item.title}**")
        for child in item.children:
            sidebar_lines.append(f"  - [{child.title}]({child.page_id}.md)")
    return "\n".join(sidebar_lines) + "\n"


def _readme_text(wiki: Wiki) -> str:
    # GitHub (and most forges) render README.md when you open the folder,
    # whereas _sidebar.md is a docsify convention and index.md is not
    # auto-rendered — so a wiki committed to a repo would otherwise show a
    # bare file list. README.md = overview + a contents map.
    readme_lines = [f"# {wiki.project_name}\n"]
    overview = wiki.get_page("index")
    if overview is not None and overview.content.strip():
        readme_lines.append(overview.content.strip())
        readme_lines.append("")
    readme_lines.append("## Contents\n")
    for item in wiki.sidebar:
        if item.page_id:
            readme_lines.append(f"- [{item.title}]({item.page_id}.md)")
        else:
            readme_lines.append(f"- **{item.title}**")
        for child in item.children:
            readme_lines.append(f"  - [{child.title}]({child.page_id}.md)")
    return "\n".join(readme_lines) + "\n"
