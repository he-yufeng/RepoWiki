"""Route-level tests for the structured symbol index endpoint."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from repowiki.core.cache import Cache
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
from repowiki.core.wiki_builder import WikiBuilder
from repowiki.server import app as app_module
from repowiki.server.models import ProjectInfo


def _client(monkeypatch, tmp_path):
    monkeypatch.setattr(app_module, "Cache", lambda: Cache(tmp_path / "cache.db"))
    return TestClient(app_module.create_app(static_dir=tmp_path / "missing"))


def test_symbols_endpoint_returns_the_markdown_index_source(monkeypatch, tmp_path):
    project = ProjectContext(
        name="demo",
        root=str(tmp_path),
        files=[
            FileInfo(path="alpha/core.py", size=10, language="python", lines=1, content="X = 1\n"),
            FileInfo(path="beta/runner.py", size=20, language="python", lines=1, content="Y = 2\n"),
        ],
    )
    graph = DependencyGraph.build_from_project(project)
    data = WikiData(
        overview=ProjectOverview(name="demo"),
        modules=[
            ModuleDoc(
                name="beta",
                files=[
                    FileDoc(
                        path="beta/runner.py",
                        key_symbols=[
                            Symbol(name="shared_helper", kind="function"),
                            Symbol(name="run_beta", kind="function", description="entry point"),
                        ],
                    )
                ],
            ),
            ModuleDoc(
                name="alpha",
                files=[
                    FileDoc(
                        path="alpha/core.py",
                        key_symbols=[
                            Symbol(name="shared_helper", kind="function"),
                            Symbol(name="AlphaEngine", kind="class", description="drives alpha"),
                        ],
                    )
                ],
            ),
        ],
    )
    wiki = WikiBuilder().build(project, data, graph)
    monkeypatch.setitem(
        app_module._projects,
        "p1",
        {
            "info": ProjectInfo(id="p1", name="demo", status="done"),
            "wiki": wiki,
            "project": project,
            "progress": [],
        },
    )

    with _client(monkeypatch, tmp_path) as client:
        body = client.get("/api/project/p1/symbols").json()
        missing = client.get("/api/project/p2/symbols").json()

    assert body["project_name"] == "demo"
    assert body["symbols"] == [
        {
            "name": "shared_helper",
            "kind": "function",
            "description": "",
            "module": "alpha",
            "page_id": "modules/alpha",
        },
        {
            "name": "run_beta",
            "kind": "function",
            "description": "entry point",
            "module": "beta",
            "page_id": "modules/beta",
        },
        {
            "name": "shared_helper",
            "kind": "function",
            "description": "",
            "module": "beta",
            "page_id": "modules/beta",
        },
        {
            "name": "AlphaEngine",
            "kind": "class",
            "description": "drives alpha",
            "module": "alpha",
            "page_id": "modules/alpha",
        },
    ]
    assert "error" in missing
