"""ingest a local directory into a ProjectContext."""

from __future__ import annotations

import json
from pathlib import Path

from repowiki.core.models import FileInfo, ProjectContext
from repowiki.core.scanner import build_file_tree, scan_directory


def _guess_project_name(root: Path, files: list[FileInfo]) -> str:
    """try to extract the project name from config files, fall back to dir name."""
    for f in files:
        if f.path == "pyproject.toml" and f.content:
            for line in f.content.splitlines():
                if line.strip().startswith("name"):
                    # name = "something"
                    val = line.split("=", 1)[-1].strip().strip('"').strip("'")
                    if val:
                        return val

        if f.path == "package.json" and f.content:
            try:
                pkg = json.loads(f.content)
                if name := pkg.get("name"):
                    return str(name).lstrip("@").replace("/", "-")
            except (json.JSONDecodeError, TypeError):
                pass

        if f.path == "Cargo.toml" and f.content:
            for line in f.content.splitlines():
                if line.strip().startswith("name"):
                    val = line.split("=", 1)[-1].strip().strip('"').strip("'")
                    if val:
                        return val

    return root.name


def ingest_local(
    path: str | Path,
    max_file_size: int = 200 * 1024,
    max_files: int = 1000,
) -> ProjectContext:
    """scan a local directory and package it into a ProjectContext."""
    root = Path(path).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Not a directory: {root}")

    files = scan_directory(root, max_file_size=max_file_size, max_files=max_files)
    name = _guess_project_name(root, files)
    tree = build_file_tree(files)

    return ProjectContext(
        name=name,
        root=str(root),
        files=files,
        file_tree=tree,
    )
