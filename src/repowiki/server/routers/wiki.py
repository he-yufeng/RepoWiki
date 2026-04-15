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
async def get_file(project_id: str, file_path: str):
    """get file content with language detection."""
    projects = get_projects()
    proj = projects.get(project_id)
    if not proj or not proj.get("project"):
        return {"error": "Project not ready"}

    project = proj["project"]
    for f in project.files:
        if f.path == file_path:
            return {
                "path": f.path,
                "language": f.language,
                "content": f.content or f.preview,
                "lines": f.lines,
            }

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
