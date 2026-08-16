"""FastAPI application for the RepoWiki web interface."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from repowiki import __version__
from repowiki.core.cache import Cache

# in-memory project store (keyed by project ID)
_projects: dict = {}
_cache: Cache | None = None


def get_cache() -> Cache:
    assert _cache is not None
    return _cache


def get_projects() -> dict:
    return _projects


def create_app():
    """factory function for creating the FastAPI app."""
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

    # serve embedded frontend (if built)
    from pathlib import Path
    static_dir = Path(__file__).parent / "static"
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True))

    return app
