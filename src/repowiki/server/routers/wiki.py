"""wiki content endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from repowiki.server.app import get_projects

router = APIRouter()


@router.get("/project/{project_id}/wiki")
async def get_wiki(project_id: str):
    """get the full wiki structure (sidebar + page list)."""
    projects = get_projects()
    proj = projects.get(project_id)
    if not proj or not proj.get("wiki"):
        return {"error": "Wiki not ready"}

    wiki = proj["wiki"]
    return {
        "project_name": wiki.project_name,
        "sidebar": _serialize_sidebar(wiki.sidebar),
        "pages": [
            {"id": p.id, "title": p.title, "order": p.order, "parent_id": p.parent_id}
            for p in wiki.pages
        ],
    }


@router.get("/project/{project_id}/wiki/{page_id:path}")
async def get_page(project_id: str, page_id: str):
    """get a single wiki page content."""
    projects = get_projects()
    proj = projects.get(project_id)
    if not proj or not proj.get("wiki"):
        return {"error": "Wiki not ready"}

    page = proj["wiki"].get_page(page_id)
    if not page:
        return {"error": f"Page '{page_id}' not found"}

    return {
        "id": page.id,
        "title": page.title,
        "content": page.content,
    }


@router.get("/project/{project_id}/file/{file_path:path}")
async def get_file(
    project_id: str,
    file_path: str,
    start: int = 0,
    end: int = 0,
):
    """get file content with language detection.

    When ``start``/``end`` are supplied (1-based, inclusive line numbers)
    the response also includes a pre-sliced ``snippet`` plus
    ``highlight_start``/``highlight_end`` so the SourceView component
    can render with the target lines highlighted without re-parsing the
    full body on the client.
    """
    projects = get_projects()
    proj = projects.get(project_id)
    if not proj or not proj.get("project"):
        return {"error": "Project not ready"}

    project = proj["project"]
    for f in project.files:
        if f.path == file_path:
            full = f.content or f.preview
            payload: dict = {
                "path": f.path,
                "language": f.language,
                "content": full,
                "lines": f.lines,
            }
            if start and end and start > 0 and end >= start:
                # Slice the body around the target range with some context
                # above/below so the user sees what surrounds the citation.
                lines = full.splitlines()
                pad = 10
                lo = max(0, start - 1 - pad)
                hi = min(len(lines), end + pad)
                payload["snippet"] = "\n".join(lines[lo:hi])
                payload["snippet_start"] = lo + 1
                payload["highlight_start"] = start
                payload["highlight_end"] = end
            return payload

    return {"error": f"File '{file_path}' not found"}


@router.get("/project/{project_id}/graph")
async def get_graph(project_id: str):
    """get the dependency graph as nodes + edges."""
    projects = get_projects()
    proj = projects.get(project_id)
    if not proj or not proj.get("project"):
        return {"error": "Project not ready"}

    from repowiki.core.graph import DependencyGraph
    graph = DependencyGraph.build_from_project(proj["project"])

    nodes = [
        {"id": n, **graph.graph.nodes[n]}
        for n in graph.graph.nodes
    ]
    edges = [
        {"source": s, "target": t}
        for s, t in graph.graph.edges
    ]
    rankings = [
        {"path": path, "score": round(score, 6)}
        for path, score in graph.rank_files()[:20]
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "rankings": rankings,
        "mermaid": graph.to_mermaid(),
    }


def _serialize_sidebar(items) -> list[dict]:
    result = []
    for item in items:
        entry = {"title": item.title, "page_id": item.page_id}
        if item.children:
            entry["children"] = _serialize_sidebar(item.children)
        result.append(entry)
    return result
