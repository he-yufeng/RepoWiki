"""Custom Hatch build hook that builds the React frontend (vite output ->
src/repowiki/server/static/) before wheels / sdists are packed.

If npm or the frontend/ directory aren't available, we print a warning and
keep going -- a backend-only wheel still installs correctly, the user just
won't get the web UI when they call ``repowiki serve``.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class FrontendBuildHook(BuildHookInterface):
    PLUGIN_NAME = "frontend-build"

    def initialize(self, version: str, build_data: dict) -> None:
        root = Path(self.root)
        frontend = root / "frontend"
        static = root / "src" / "repowiki" / "server" / "static"

        if not frontend.is_dir():
            self.app.display_warning(
                f"frontend/ not found at {frontend} -- packing without web UI"
            )
            return

        npm = shutil.which("npm") or shutil.which("npm.cmd")
        if not npm:
            self.app.display_warning(
                "npm not found in PATH -- packing without web UI. "
                "Install Node.js >=20 to bundle the React frontend."
            )
            return

        # If static/ already has a fresh index.html (e.g. CI built it in a
        # previous step), don't rebuild -- saves ~30s on every wheel build.
        if (static / "index.html").exists() and self._is_static_fresh(frontend, static):
            self.app.display_info(f"Reusing existing build in {static}")
            return

        self.app.display_info("Installing frontend dependencies (npm ci)...")
        self._run([npm, "ci", "--no-audit", "--no-fund"], cwd=frontend)

        self.app.display_info("Building frontend (vite build)...")
        self._run([npm, "run", "build"], cwd=frontend)

        if not (static / "index.html").exists():
            raise RuntimeError(
                f"vite build did not produce {static / 'index.html'}"
            )
        self.app.display_success(f"Frontend built into {static}")

    @staticmethod
    def _is_static_fresh(frontend: Path, static: Path) -> bool:
        """static/ is fresh if every file under it is newer than every
        non-node_modules source file in frontend/."""
        try:
            static_oldest = min(
                p.stat().st_mtime for p in static.rglob("*") if p.is_file()
            )
        except ValueError:
            return False

        for p in frontend.rglob("*"):
            if not p.is_file():
                continue
            if "node_modules" in p.parts or "dist" in p.parts:
                continue
            if p.stat().st_mtime > static_oldest:
                return False
        return True

    @staticmethod
    def _run(cmd: list[str], cwd: Path) -> None:
        subprocess.run(cmd, cwd=str(cwd), check=True)
