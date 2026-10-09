"""Route-level tests for the insights router (repo map and diff review)."""

from __future__ import annotations

import subprocess

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")  # TestClient dependency

from fastapi.testclient import TestClient

from repowiki.core.cache import Cache
from repowiki.core.models import ProjectContext
from repowiki.core.scanner import scan_directory
from repowiki.server import app as app_module
from repowiki.server.models import ProjectInfo


def _client(monkeypatch, tmp_path):
    # keep the lifespan cache out of the real home directory
    monkeypatch.setattr(app_module, "Cache", lambda: Cache(tmp_path / "cache.db"))
    return TestClient(app_module.create_app(static_dir=tmp_path / "missing"))


def _git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _make_git_repo(repo):
    subprocess.run(
        ["git", "init", "-b", "main", str(repo)], check=True, capture_output=True
    )
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    (repo / "core").mkdir()
    (repo / "core" / "engine.py").write_text(
        "from .store import save\n\ndef run(): ...\n"
    )
    (repo / "core" / "store.py").write_text("from .cache import warm\n\ndef save(): ...\n")
    (repo / "core" / "cache.py").write_text("def warm(): ...\n")
    (repo / "notes.py").write_text("# orphan\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "base")


def _seed_project(monkeypatch, root, project_id="p1"):
    files = scan_directory(str(root))
    project = ProjectContext(name="demo", root=str(root), files=files)
    monkeypatch.setitem(app_module._projects, project_id, {
        "info": ProjectInfo(id=project_id, name="demo", status="done"),
        "wiki": None,
        "project": project,
        "progress": [],
    })


# --- repo map ---

def test_map_ranks_imported_utilities_first(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    _make_git_repo(repo)
    _seed_project(monkeypatch, repo)

    with _client(monkeypatch, tmp_path) as client:
        body = client.get("/api/project/p1/map").json()

    assert body["file_count"] == 4
    # store.py imports cache.py directly, engine.py transitively
    top = body["entries"][0]
    assert top["rank"] == 1
    assert top["path"] == "core/cache.py"
    assert top["language"] == "python"
    assert top["lines"] >= 1
    assert top["score"] > 0
    assert {e["path"] for e in body["entries"]} == {
        "core/cache.py", "core/store.py", "core/engine.py", "notes.py",
    }


def test_map_top_parameter_caps_and_validates(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    _make_git_repo(repo)
    _seed_project(monkeypatch, repo)

    with _client(monkeypatch, tmp_path) as client:
        assert len(client.get("/api/project/p1/map?top=2").json()["entries"]) == 2
        bad = client.get("/api/project/p1/map?top=0")
        assert bad.status_code == 400
        assert client.get("/api/project/nope/map").status_code == 404


# --- diff review ---

def test_diff_returns_changed_files_in_review_order(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    _make_git_repo(repo)
    (repo / "core" / "cache.py").write_text("def warm(): ...\n# changed\n")
    (repo / "core" / "new_mod.py").write_text("def fresh(): ...\n")
    _git(repo, "add", "core/new_mod.py")
    _seed_project(monkeypatch, repo)

    with _client(monkeypatch, tmp_path) as client:
        resp = client.post("/api/project/p1/diff", json={"refspec": "HEAD"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["refspec"] == "HEAD"
    assert body["changed"] == 2
    cache = body["entries"][0]
    assert cache["path"] == "core/cache.py"
    assert cache["change"] == "M"
    assert cache["rank"] == 1
    assert cache["direct_dependents"] == 1
    assert cache["transitive_dependents"] == 2
    fresh = body["entries"][1]
    assert fresh["path"] == "core/new_mod.py"
    assert fresh["change"] == "A"


def test_diff_unknown_project_and_bad_refspec(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    _make_git_repo(repo)
    _seed_project(monkeypatch, repo)

    with _client(monkeypatch, tmp_path) as client:
        assert client.post("/api/project/nope/diff", json={}).status_code == 404
        bad = client.post("/api/project/p1/diff", json={"refspec": "HEAD~99"})
        assert bad.status_code == 400
        assert "cannot diff" in bad.json()["error"]
        empty = client.post("/api/project/p1/diff", json={"refspec": "  "})
        assert empty.status_code == 400


def test_diff_on_shallow_clone_adds_hint(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    _make_git_repo(repo)
    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "--depth", "1", f"file://{repo}", str(shallow)],
        check=True, capture_output=True,
    )
    _seed_project(monkeypatch, shallow)

    with _client(monkeypatch, tmp_path) as client:
        resp = client.post("/api/project/p1/diff", json={"refspec": "HEAD~1"})

    assert resp.status_code == 400
    assert "shallow" in resp.json()["error"]
