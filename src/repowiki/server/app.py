"""FastAPI application for the RepoWiki web interface."""

from __future__ import annotations

from contextlib import asynccontextmanager

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
        yield
        await _cache.close()

    app = FastAPI(
        title="RepoWiki",
        description="Generate wiki documentation for any codebase",
        version="0.1.0",
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
        return {"status": "ok", "version": "0.1.0"}

    # serve embedded frontend (if built)
    from pathlib import Path
    static_dir = Path(__file__).parent / "static"
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True))

    return app
