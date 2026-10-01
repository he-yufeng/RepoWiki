"""Route-level tests for the scan and wiki routers."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")  # TestClient dependency

from fastapi.testclient import TestClient

from repowiki.core.cache import Cache
from repowiki.core.models import FileInfo, ProjectContext
from repowiki.core.wiki_builder import SidebarItem, Wiki, WikiPage
from repowiki.server import app as app_module
from repowiki.server.models import ProjectInfo
from repowiki.server.routers import scan as scan_module


def _client(monkeypatch, tmp_path):
    # keep the lifespan cache out of the real home directory
    monkeypatch.setattr(app_module, "Cache", lambda: Cache(tmp_path / "cache.db"))
    return TestClient(app_module.create_app(static_dir=tmp_path / "missing"))


def _file(path: str, content: str, *, with_content: bool = True) -> FileInfo:
    return FileInfo(
        path=path,
        size=len(content),
        language="python",
        lines=content.count("\n") + 1,
        preview=content[:200],
        content=content if with_content else "",
    )


def _seed_wiki_project(monkeypatch, *, wiki_ready: bool = True) -> None:
    project = ProjectContext(
        name="demo",
        root="/demo",
        files=[
            _file("app.py", "import util\nutil.run()\n"),
            _file("util.py", "def run():\n    pass\n"),
            _file("big.py", "x = 1\n" * 500, with_content=False),
        ],
        file_tree="app.py\nutil.py\nbig.py",
    )
    wiki = Wiki(
        project_name="demo",
        pages=[
            WikiPage(id="index", title="Overview", content="# demo\n"),
            WikiPage(id="modules/util", title="util", content="utilities\n",
                     parent_id="index", order=1),
        ],
        sidebar=[
            SidebarItem(title="Overview", page_id="index",
                        children=[SidebarItem(title="util", page_id="modules/util")]),
        ],
    )
    monkeypatch.setitem(app_module._projects, "p1", {
        "info": ProjectInfo(id="p1", name="demo", status="done"),
        "wiki": wiki if wiki_ready else None,
        "project": project,
        "progress": ["Ingesting project...", "Done!"],
    })


# --- scan router ---

def test_scan_registers_project_and_background_task_runs(monkeypatch, tmp_path):
    seen = {}

    async def stub_scan(project_id, req, user_api_key):
        proj = app_module._projects[project_id]
        proj["info"].status = "done"
        seen["args"] = (req.path, user_api_key)

    monkeypatch.setattr(scan_module, "_run_scan", stub_scan)

    with _client(monkeypatch, tmp_path) as client:
        resp = client.post("/api/scan", json={"path": "/tmp/x"},
                           headers={"x-api-key": "key-123"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "pending"
        pid = body["id"]
        assert pid in app_module._projects

    # TestClient runs background tasks before returning from the with block
    assert app_module._projects[pid]["info"].status == "done"
    assert seen["args"] == ("/tmp/x", "key-123")

    app_module._projects.pop(pid, None)


def test_get_project_known_and_unknown(monkeypatch, tmp_path):
    _seed_wiki_project(monkeypatch)

    with _client(monkeypatch, tmp_path) as client:
        assert client.get("/api/project/p1").json()["name"] == "demo"
        assert client.get("/api/project/nope").json() == {"error": "Project not found"}


def test_status_stream_replays_progress_then_done(monkeypatch, tmp_path):
    _seed_wiki_project(monkeypatch)

    with _client(monkeypatch, tmp_path) as client:
        body = client.get("/api/project/p1/status").text
        assert '"step": "Ingesting project..."' in body
        assert '"status": "done"' in body
        assert '"error": "not found"' in client.get("/api/project/nope/status").text


# --- wiki router ---

def test_wiki_returns_sidebar_and_pages(monkeypatch, tmp_path):
    _seed_wiki_project(monkeypatch)

    with _client(monkeypatch, tmp_path) as client:
        body = client.get("/api/project/p1/wiki").json()

    assert body["project_name"] == "demo"
    assert body["sidebar"] == [{
        "title": "Overview",
        "page_id": "index",
        "children": [{"title": "util", "page_id": "modules/util"}],
    }]
    assert [p["id"] for p in body["pages"]] == ["index", "modules/util"]
    assert body["pages"][1]["parent_id"] == "index"


def test_wiki_not_ready_and_unknown_project(monkeypatch, tmp_path):
    _seed_wiki_project(monkeypatch, wiki_ready=False)

    with _client(monkeypatch, tmp_path) as client:
        assert client.get("/api/project/p1/wiki").json() == {"error": "Wiki not ready"}
        assert client.get("/api/project/nope/wiki").json() == {"error": "Wiki not ready"}


def test_get_page_found_and_missing(monkeypatch, tmp_path):
    _seed_wiki_project(monkeypatch)

    with _client(monkeypatch, tmp_path) as client:
        page = client.get("/api/project/p1/wiki/modules/util").json()
        assert page["title"] == "util"
        assert page["content"] == "utilities\n"
        missing = client.get("/api/project/p1/wiki/modules/nope").json()
        assert missing == {"error": "Page 'modules/nope' not found"}


def test_get_file_falls_back_to_preview(monkeypatch, tmp_path):
    _seed_wiki_project(monkeypatch)

    with _client(monkeypatch, tmp_path) as client:
        full = client.get("/api/project/p1/file/util.py").json()
        assert full["content"].startswith("def run():")
        # content-less files serve the preview instead of an empty page
        big = client.get("/api/project/p1/file/big.py").json()
        assert big["content"] == ("x = 1\n" * 500)[:200]  # preview is capped at 200 chars
        assert client.get("/api/project/p1/file/nope.py").json() == {
            "error": "File 'nope.py' not found"
        }


def test_graph_endpoint_returns_nodes_edges_rankings(monkeypatch, tmp_path):
    _seed_wiki_project(monkeypatch)

    with _client(monkeypatch, tmp_path) as client:
        body = client.get("/api/project/p1/graph").json()

    assert {n["id"] for n in body["nodes"]} == {"app.py", "util.py", "big.py"}
    assert len(body["edges"]) == 1  # app.py -> util.py
    assert body["rankings"]
    # mermaid only renders inter-module deps, and these files share one module
    assert body["mermaid"] == ""


def test_graph_not_ready(monkeypatch, tmp_path):
    _seed_wiki_project(monkeypatch)
    app_module._projects["p1"]["project"] = None

    with _client(monkeypatch, tmp_path) as client:
        assert client.get("/api/project/p1/graph").json() == {"error": "Project not ready"}
