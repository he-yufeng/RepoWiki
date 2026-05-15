"""resolve a git ref into the set of changed file paths."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def changed_paths_since(repo_root: str | Path, ref: str) -> set[str]:
    """Return repo-relative paths changed between ``ref`` and HEAD,
    plus anything in the working tree that isn't committed yet.

    Returns an empty set if the directory isn't a git repo or git
    isn't installed -- callers should treat that as "incremental
    mode unavailable" and fall back to a full re-analysis.
    """
    root = Path(repo_root)
    if not (root / ".git").exists():
        logger.info("Not a git repo: %s", root)
        return set()

    try:
        # range diff between ref and HEAD (committed changes)
        committed = _run_git(
            root,
            ["git", "diff", "--name-only", f"{ref}...HEAD"],
        )
        # uncommitted working-tree changes vs HEAD
        working = _run_git(
            root,
            ["git", "diff", "--name-only", "HEAD"],
        )
        # also include staged-but-not-committed
        staged = _run_git(
            root,
            ["git", "diff", "--name-only", "--cached"],
        )
        # untracked
        untracked = _run_git(
            root,
            ["git", "ls-files", "--others", "--exclude-standard"],
        )
    except subprocess.CalledProcessError as e:
        logger.warning("git diff failed: %s", e.stderr.strip() if e.stderr else e)
        return set()
    except FileNotFoundError:
        logger.warning("git executable not found")
        return set()

    paths: set[str] = set()
    for output in (committed, working, staged, untracked):
        for line in output.splitlines():
            line = line.strip()
            if line:
                # normalise to forward slash to match scanner output
                paths.add(line.replace("\\", "/"))
    return paths


def _run_git(root: Path, cmd: list[str]) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(root),
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return result.stdout
