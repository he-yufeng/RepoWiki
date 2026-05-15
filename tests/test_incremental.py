"""Incremental scan: --since git ref skips unchanged modules."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from repowiki.core.analyzer import Analyzer
from repowiki.core.cache import Cache
from repowiki.core.models import FileInfo, ProjectContext
from repowiki.ingest.git_diff import changed_paths_since

# --- git_diff helper ---------------------------------------------------------

def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(
        ["git", *args], cwd=str(cwd), check=True,
        capture_output=True, text=True,
    )


def test_changed_paths_in_non_git_dir(tmp_path):
    """no .git -> empty set, callers should fall back to full scan."""
    assert changed_paths_since(tmp_path, "HEAD~1") == set()


def test_changed_paths_picks_up_committed_and_untracked(tmp_path):
    _git(["init", "-q", "-b", "main"], tmp_path)
    _git(["config", "user.email", "t@t"], tmp_path)
    _git(["config", "user.name", "t"], tmp_path)

    (tmp_path / "old.py").write_text("v1\n")
    _git(["add", "."], tmp_path)
    _git(["commit", "-q", "-m", "initial"], tmp_path)

    (tmp_path / "old.py").write_text("v2\n")  # committed-after-base change
    _git(["add", "."], tmp_path)
    _git(["commit", "-q", "-m", "edit"], tmp_path)

    (tmp_path / "untracked.py").write_text("new\n")  # working tree
    (tmp_path / "another.py").write_text("staged\n")
    _git(["add", "another.py"], tmp_path)

    paths = changed_paths_since(tmp_path, "HEAD~1")
    assert "old.py" in paths
    assert "untracked.py" in paths
    assert "another.py" in paths


# --- analyzer behaviour ------------------------------------------------------

class _RecordingLLM:
    def __init__(self):
        self.calls = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

    async def complete(self, messages, **_kwargs):
        self.calls += 1
        # return a no-op JSON so analyzer's downstream parsing is happy
        return '{"name": "x", "purpose": "ok"}'


def _project(paths: list[str]) -> ProjectContext:
    files = [
        FileInfo(path=p, size=10, language="python",
                 lines=1, preview="x", content="x")
        for p in paths
    ]
    return ProjectContext(name="x", root="/tmp/x", files=files,
                          file_tree="\n".join(paths))


@pytest.mark.asyncio
async def test_unchanged_modules_skipped_in_incremental_mode(tmp_path):
    cache = Cache(db_path=tmp_path / "cache.db")
    await cache.init()

    # spread across distinct top-level dirs so they become separate modules
    project = _project([
        "frontend/main.tsx",
        "frontend/util.ts",
        "backend/api.py",
        "backend/db.py",
        "scripts/build.sh",
    ])

    llm = _RecordingLLM()
    analyzer = Analyzer(
        llm=llm, cache=cache, concurrency=1,
        # only frontend changed -> backend + scripts modules skip the LLM
        changed_paths={"frontend/main.tsx"},
    )

    await analyzer.analyze(project)
    await cache.close()

    assert "backend" in analyzer.skipped_modules
    assert "scripts" in analyzer.skipped_modules
    # frontend stays
    assert "frontend" not in analyzer.skipped_modules


@pytest.mark.asyncio
async def test_full_mode_calls_llm_for_every_module(tmp_path):
    cache = Cache(db_path=tmp_path / "cache.db")
    await cache.init()

    project = _project([
        "frontend/main.tsx",
        "backend/api.py",
    ])

    llm = _RecordingLLM()
    analyzer = Analyzer(llm=llm, cache=cache, concurrency=1, changed_paths=None)
    await analyzer.analyze(project)
    await cache.close()

    assert analyzer.skipped_modules == []
    # overview + arch + guide + 2 modules = 5 calls
    assert llm.calls >= 5
