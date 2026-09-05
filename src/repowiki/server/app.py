"""FastAPI application for the RepoWiki web interface."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from repowiki import __version__
from repowiki.core.cache import Cache

# shown at / when the built frontend is not installed alongside the package
_NO_FRONTEND_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RepoWiki web UI not built</title>
<style>
body { font-family: system-ui, sans-serif; max-width: 42rem; margin: 4rem auto; padding: 0 1rem; line-height: 1.6; color: #1f2328; }
code, pre { background: #f6f8fa; border-radius: 6px; }
code { padding: 0.15em 0.4em; }
pre { padding: 0.8rem 1rem; }
</style>
</head>
<body>
<h1>RepoWiki web UI is not available</h1>
<p>The API itself is running, see <a href="/docs">/docs</a>, but this
installation does not contain the built frontend.</p>
<p>Wheels published to PyPI ship the web UI. If you installed from PyPI and
ended up here, please
<a href="https://github.com/he-yufeng/RepoWiki/issues">open an issue</a>.</p>
<p>Running from a source checkout? Build the frontend once, then restart:</p>
<pre>cd frontend
npm ci
npm run build</pre>
<p>The build output lands in <code>src/repowiki/server/static</code> and is
served on the next start.</p>
</body>
</html>"""

# in-memory project store (keyed by project ID)
_projects: dict = {}
_cache: Cache | None = None


def get_cache() -> Cache:
    assert _cache is not None
    return _cache


def get_projects() -> dict:
    return _projects


def create_app(static_dir: str | Path | None = None):
    """factory function for creating the FastAPI app.

    static_dir overrides the bundled frontend location; defaults to the
    static directory shipped inside the package (or built from frontend/).
    """
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.staticfiles import StaticFiles
    except ImportError:
        raise RuntimeError(
            "FastAPI not installed. Run: pip install repowiki[web]"
        )

    @asynccontextmanager
    async def lifespan(app):
        global _cache
        _cache = Cache()
        await _cache.init()

        # `repowiki serve <path|url>` preloads that project instead of
        # starting the UI empty.
        serve_target = os.environ.pop("REPOWIKI_SERVE_TARGET", None)
        if serve_target:
            import uuid

            from repowiki.server.models import ScanRequest
            from repowiki.server.routers.scan import _run_scan

            project_id = str(uuid.uuid4())[:8]
            from repowiki.server.models import ProjectInfo

            info = ProjectInfo(id=project_id, name="", status="pending")
            _projects[project_id] = {"info": info, "wiki": None, "project": None, "progress": []}
            if "://" in serve_target:
                req = ScanRequest(url=serve_target)
            else:
                req = ScanRequest(path=serve_target)
            asyncio.create_task(_run_scan(project_id, req, None))

        yield
        await _cache.close()

    app = FastAPI(
        title="RepoWiki",
        description="Generate wiki documentation for any codebase",
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # register routers
    from repowiki.server.routers import chat, scan, wiki
    app.include_router(scan.router, prefix="/api")
    app.include_router(wiki.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": __version__}

    # serve the embedded frontend; a missing or partial build used to answer
    # / with a bare 404, so point at the PyPI wheel or the frontend build instead
    static_path = Path(static_dir) if static_dir is not None else Path(__file__).parent / "static"
    if (static_path / "index.html").is_file():
        app.mount("/", StaticFiles(directory=str(static_path), html=True))
    else:
        from fastapi.responses import HTMLResponse

        @app.get("/", response_class=HTMLResponse, include_in_schema=False)
        async def frontend_not_built():
            return _NO_FRONTEND_PAGE

    return app
