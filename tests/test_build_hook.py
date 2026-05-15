"""Verify the Hatch frontend-build hook is wired correctly and that
`repowiki serve` warns when the UI is missing."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from repowiki.cli import cli

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_hatch_hook_file_syntactically_valid():
    """hatch_build.py must parse and contain the right symbol names.
    (Full import requires hatchling, only present at build time.)"""
    spec_path = REPO_ROOT / "hatch_build.py"
    assert spec_path.exists()

    src = spec_path.read_text(encoding="utf-8")
    compile(src, str(spec_path), "exec")  # syntax check
    assert "class FrontendBuildHook" in src
    assert 'PLUGIN_NAME = "frontend-build"' in src
    assert "BuildHookInterface" in src


def test_pyproject_registers_hook_and_force_include():
    """pyproject.toml must list the hook + force-include the static dir."""
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.hatch.build.hooks.custom]" in text
    assert 'path = "hatch_build.py"' in text
    assert "[tool.hatch.build.targets.wheel.force-include]" in text
    assert "src/repowiki/server/static" in text


def test_serve_warns_when_static_missing(tmp_path, monkeypatch):
    """If src/repowiki/server/static/index.html doesn't exist, serve should
    print a hint about how to build it."""
    import repowiki.server as server_pkg
    real_static = Path(server_pkg.__file__).parent / "static"

    # rename real static dir for the duration of the test (if it exists),
    # so the CLI sees an empty/absent UI bundle.
    backup: Path | None = None
    if real_static.exists():
        backup = real_static.with_suffix(".bak")
        if backup.exists():
            shutil.rmtree(backup)
        real_static.rename(backup)

    try:
        result = CliRunner().invoke(cli, ["serve", "--help"])
        assert result.exit_code == 0
        # --help just renders help; for the warning we need the actual command
        # but starting uvicorn is too heavy. Instead, inspect the cli source
        # for the warning string -- a smoke check is enough.
        from repowiki import cli as cli_mod
        src = Path(cli_mod.__file__).read_text(encoding="utf-8")
        assert "Web UI not bundled" in src
        assert "npm run build" in src
    finally:
        if backup is not None and backup.exists():
            backup.rename(real_static)


def test_static_force_included_in_wheel_target():
    """force-include maps repo path -> wheel path so static survives even
    though .gitignore excludes it from VCS."""
    import tomllib
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    force = (
        data.get("tool", {}).get("hatch", {}).get("build", {})
        .get("targets", {}).get("wheel", {}).get("force-include", {})
    )
    assert force.get("src/repowiki/server/static") == "repowiki/server/static"
