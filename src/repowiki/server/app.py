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

    # NOTE: this allow-list targets local development with Vite (5173) and
    # CRA (3000). Production deployments behind a real domain should
    # override this -- either patch this list, or front the app with a
    # reverse proxy and same-origin requests. Don't widen to "*" because
    # the chat endpoint accepts user-supplied API keys via x-api-key.
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

    # serve embedded frontend (if built). The custom subclass returns the
    # SPA's index.html for any path the bundle doesn't contain, so deep
    # links like /project/<id>/source resolve through react-router instead
    # of hitting a 404 wall when the user reloads or shares a URL.
    from pathlib import Path

    from starlette.exceptions import HTTPException as StarletteHTTPException
    from starlette.responses import FileResponse

    static_dir = Path(__file__).parent / "static"
    if static_dir.is_dir():
        index_path = static_dir / "index.html"

        class SpaStaticFiles(StaticFiles):
            async def get_response(self, path, scope):
                # Starlette's StaticFiles raises HTTPException(404) when
                # the requested file isn't on disk; older versions return a
                # 404 Response instead. Handle both, but never hijack API
                # paths -- those must keep their real 404.
                if path.startswith("api/"):
                    return await super().get_response(path, scope)
                try:
                    response = await super().get_response(path, scope)
                except StarletteHTTPException as exc:
                    if exc.status_code == 404 and index_path.is_file():
                        return FileResponse(str(index_path))
                    raise
                if response.status_code == 404 and index_path.is_file():
                    return FileResponse(str(index_path))
                return response

        app.mount("/", SpaStaticFiles(directory=str(static_dir), html=True))

    return app
