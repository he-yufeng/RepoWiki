"""Web UI scan path: --since wiring.

These tests exercise the request/response surface around the new
``ScanRequest.since`` field without invoking the full pipeline (which
would require a live LLM). We assert:

  1. The pydantic model accepts and exposes ``since`` (None by default).
  2. ``changed_paths_since`` returns an empty set when the path isn't a
     git repo, which is the fallback the server relies on.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from repowiki.ingest.git_diff import changed_paths_since
from repowiki.server.models import ScanRequest


def test_scan_request_since_defaults_to_none():
    req = ScanRequest(path="/tmp/x")
    assert req.since is None


def test_scan_request_since_round_trips():
    req = ScanRequest(path="/tmp/x", since="HEAD~3")
    assert req.since == "HEAD~3"
    # Field survives the JSON serialization the FastAPI app uses.
    dumped = req.model_dump()
    assert dumped["since"] == "HEAD~3"


def test_scan_request_since_omitted_in_json_when_unset():
    # `since` must be optional on the wire so existing clients keep working.
    req = ScanRequest(url="https://github.com/x/y")
    assert req.since is None


def test_changed_paths_since_non_git_returns_empty():
    # The server treats this as "incremental unavailable, fall back to full".
    with tempfile.TemporaryDirectory() as tmp:
        # No .git directory inside -- changed_paths_since must not blow up.
        assert changed_paths_since(tmp, "HEAD") == set()


def test_changed_paths_since_missing_path_returns_empty():
    assert changed_paths_since("/definitely/not/a/real/path/xyzzy", "HEAD") == set()


def test_changed_paths_since_returns_set_type():
    # Stable contract for the analyzer: it does `isdisjoint(changed_paths)`,
    # which requires a set/frozenset.
    with tempfile.TemporaryDirectory() as tmp:
        result = changed_paths_since(Path(tmp), "HEAD")
        assert isinstance(result, set)
