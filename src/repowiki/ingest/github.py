"""clone a remote git repository and ingest it."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path

from repowiki.core.models import ProjectContext
from repowiki.ingest.local import ingest_local

logger = logging.getLogger(__name__)

_CLONE_DIR = Path.home() / ".repowiki" / "repos"
_CLONE_TIMEOUT = 120  # seconds
_MAX_REPO_SIZE_MB = 500

# matches github/gitlab/bitbucket URLs in various formats
_GIT_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?"
    r"(github\.com|gitlab\.com|bitbucket\.org)"
    r"/([^/\s]+)/([^/\s#?.]+)"
)


def parse_git_url(url: str) -> tuple[str, str, str] | None:
    """extract (host, owner, repo) from a git URL. returns None if not recognized."""
    url = url.strip().rstrip("/")
    # strip trailing .git
    if url.endswith(".git"):
        url = url[:-4]

    m = _GIT_URL_RE.search(url)
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3)


def _clone_url(url: str) -> str:
    """normalize a URL to a proper git clone URL."""
    parsed = parse_git_url(url)
    if not parsed:
        return url  # let git figure it out
    host, owner, repo = parsed
    return f"https://{host}/{owner}/{repo}.git"


def ingest_github(
    url: str,
    max_file_size: int = 200 * 1024,
    max_files: int = 1000,
    force_reclone: bool = False,
) -> ProjectContext:
    """shallow-clone a git repo and return a ProjectContext."""
    parsed = parse_git_url(url)
    if not parsed:
        raise ValueError(f"Can't parse git URL: {url}")

    host, owner, repo = parsed
    dest = _CLONE_DIR / host / owner / repo

    if dest.exists():
        if force_reclone:
            shutil.rmtree(dest)
        else:
            logger.info("Using cached clone: %s", dest)
            return ingest_local(dest, max_file_size=max_file_size, max_files=max_files)

    dest.parent.mkdir(parents=True, exist_ok=True)
    clone_url = _clone_url(url)
    logger.info("Cloning %s -> %s", clone_url, dest)

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", clone_url, str(dest)],
            timeout=_CLONE_TIMEOUT,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        # clean up partial clone
        if dest.exists():
            shutil.rmtree(dest)
        raise RuntimeError(f"Clone timed out after {_CLONE_TIMEOUT}s: {clone_url}")
    except subprocess.CalledProcessError as e:
        if dest.exists():
            shutil.rmtree(dest)
        raise RuntimeError(f"Clone failed: {e.stderr.strip()}")

    # check repo size
    total_mb = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file()) / (1024 * 1024)
    if total_mb > _MAX_REPO_SIZE_MB:
        shutil.rmtree(dest)
        raise RuntimeError(
            f"Repo too large ({total_mb:.0f} MB > {_MAX_REPO_SIZE_MB} MB limit)"
        )

    return ingest_local(dest, max_file_size=max_file_size, max_files=max_files)
