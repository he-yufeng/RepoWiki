"""export wiki as a single JSON file."""

from __future__ import annotations

import json
from pathlib import Path

from repowiki.core.wiki_builder import Wiki


def export_json(wiki: Wiki, output_path: str | Path) -> bool:
    """write the full wiki structure as a JSON file.

    Returns False when the existing file already holds the same content and is
    left untouched, so repeat exports don't churn the file (or anything
    watching its mtime).
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "project_name": wiki.project_name,
        "pages": [
            {
                "id": p.id,
                "title": p.title,
                "content": p.content,
                "parent_id": p.parent_id,
                "order": p.order,
            }
            for p in wiki.pages
        ],
        "sidebar": _serialize_sidebar(wiki.sidebar),
    }

    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if out.exists() and out.read_text(encoding="utf-8") == text:
        return False
    out.write_text(text, encoding="utf-8")
    return True


def _serialize_sidebar(items) -> list[dict]:
    result = []
    for item in items:
        entry = {"title": item.title, "page_id": item.page_id}
        if item.children:
            entry["children"] = _serialize_sidebar(item.children)
        result.append(entry)
    return result
