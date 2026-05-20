"""Tests for the deterministic project-id derivation in the scan router.

The on-disk RAG snapshot is keyed by project_id. If the id were random per
scan, the snapshot would be orphaned on every server restart and the
incremental-reload code path would be dead. These tests pin the property.
"""

from __future__ import annotations

from repowiki.server.models import ScanRequest
from repowiki.server.routers.scan import _project_id_for


def test_project_id_is_stable_for_same_path(tmp_path):
    req = ScanRequest(path=str(tmp_path))
    assert _project_id_for(req) == _project_id_for(req)


def test_project_id_differs_across_paths(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    assert _project_id_for(ScanRequest(path=str(a))) != _project_id_for(
        ScanRequest(path=str(b))
    )


def test_project_id_canonicalises_relative_and_absolute(tmp_path, monkeypatch):
    # Relative and absolute forms of the same target must collide so the
    # snapshot is reused regardless of which form the user typed.
    monkeypatch.chdir(tmp_path)
    sub = tmp_path / "demo"
    sub.mkdir()
    abs_id = _project_id_for(ScanRequest(path=str(sub)))
    rel_id = _project_id_for(ScanRequest(path="demo"))
    assert abs_id == rel_id


def test_project_id_is_short_hex():
    pid = _project_id_for(ScanRequest(path="/tmp/whatever"))
    assert len(pid) == 8
    int(pid, 16)  # raises if not hex


def test_project_id_uses_url_when_no_path():
    a = _project_id_for(ScanRequest(url="https://github.com/foo/bar"))
    b = _project_id_for(ScanRequest(url="https://github.com/foo/baz"))
    assert a != b
    assert a == _project_id_for(ScanRequest(url="https://github.com/foo/bar"))
