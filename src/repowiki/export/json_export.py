"""export wiki as a single JSON file."""

from __future__ import annotations

import json
from pathlib import Path

from repowiki.core.wiki_builder import Wiki


def export_json(wiki: Wiki, output_path: str | Path) -> None:
    """write the full wiki structure as a JSON file."""
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

    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _serialize_sidebar(items) -> list[dict]:
    result = []
    for item in items:
        entry = {"title": item.title, "page_id": item.page_id}
        if item.children:
            entry["children"] = _serialize_sidebar(item.children)
        result.append(entry)
    return result
