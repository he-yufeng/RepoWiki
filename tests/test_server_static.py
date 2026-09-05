"""`repowiki serve` must never answer / with a bare 404."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")  # TestClient dependency

from fastapi.testclient import TestClient

from repowiki.core.cache import Cache
from repowiki.server import app as app_module


def _client(monkeypatch, tmp_path, static_dir):
    # keep the lifespan cache out of the real home directory
    monkeypatch.setattr(app_module, "Cache", lambda: Cache(tmp_path / "cache.db"))
    return TestClient(app_module.create_app(static_dir=static_dir))


def test_root_serves_built_frontend(monkeypatch, tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html><body>repowiki ui</body></html>", encoding="utf-8")

    with _client(monkeypatch, tmp_path, static) as client:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "repowiki ui" in resp.text
        assert client.get("/api/health").status_code == 200


def test_root_without_frontend_shows_build_instructions(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path, tmp_path / "missing") as client:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "npm run build" in resp.text
        assert "PyPI" in resp.text
        assert client.get("/api/health").status_code == 200


def test_root_with_partial_frontend_shows_build_instructions(monkeypatch, tmp_path):
    static = tmp_path / "static"
    static.mkdir()  # dir exists but index.html never landed there

    with _client(monkeypatch, tmp_path, static) as client:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "npm run build" in resp.text
