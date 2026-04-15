"""scan and project management endpoints."""

from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, BackgroundTasks, Header
from fastapi.responses import StreamingResponse

from repowiki.config import Config, resolve_model
from repowiki.server.app import get_cache, get_projects
from repowiki.server.models import ProjectInfo, ScanRequest

router = APIRouter()


@router.post("/scan", response_model=ProjectInfo)
async def start_scan(req: ScanRequest, background_tasks: BackgroundTasks,
                     x_api_key: str | None = Header(None)):
    project_id = str(uuid.uuid4())[:8]
    info = ProjectInfo(id=project_id, name="", status="pending")
    projects = get_projects()
    projects[project_id] = {"info": info, "wiki": None, "project": None, "progress": []}

    background_tasks.add_task(_run_scan, project_id, req, x_api_key)
    return info


@router.get("/project/{project_id}")
async def get_project(project_id: str):
    projects = get_projects()
    if project_id not in projects:
        return {"error": "Project not found"}
    return projects[project_id]["info"]


@router.get("/project/{project_id}/status")
async def stream_status(project_id: str):
    """SSE endpoint for scan progress updates."""
    async def event_stream():
        projects = get_projects()
        if project_id not in projects:
            yield f"data: {json.dumps({'error': 'not found'})}\n\n"
            return

        seen = 0
        while True:
            proj = projects.get(project_id)
            if not proj:
                break

            progress = proj.get("progress", [])
            while seen < len(progress):
                yield f"data: {json.dumps({'step': progress[seen]})}\n\n"
                seen += 1

            if proj["info"].status in ("done", "error"):
                yield f"data: {json.dumps({'status': proj['info'].status})}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


async def _run_scan(project_id: str, req: ScanRequest, user_api_key: str | None):
    """background task that runs the full scan + analysis pipeline."""
    projects = get_projects()
    proj = projects[project_id]
    proj["info"].status = "scanning"

    try:
        cfg = Config.load()
        if req.language:
            cfg.language = req.language
        if req.model:
            cfg.model = resolve_model(req.model)
        if user_api_key:
            cfg.api_key = user_api_key
        elif req.api_key:
            cfg.api_key = req.api_key

        def progress(msg: str):
            proj["progress"].append(msg)

        # ingest
        progress("Ingesting project...")
        if req.url:
            from repowiki.ingest.github import ingest_github
            project = ingest_github(req.url, max_file_size=cfg.max_file_size, max_files=cfg.max_files)
        elif req.path:
            from repowiki.ingest.local import ingest_local
            project = ingest_local(req.path, max_file_size=cfg.max_file_size, max_files=cfg.max_files)
        else:
            raise ValueError("Either path or url must be provided")

        proj["project"] = project
        proj["info"].name = project.name
        proj["info"].total_files = len(project.files)
        proj["info"].total_lines = project.total_lines

        # check if we have an API key
        if not cfg.api_key:
            proj["info"].status = "error"
            proj["info"].error = "No API key configured"
            return

        # analyze
        from repowiki.core.analyzer import Analyzer
        from repowiki.core.graph import DependencyGraph
        from repowiki.core.wiki_builder import WikiBuilder
        from repowiki.llm.client import LLMClient

        cache = get_cache()
        llm = LLMClient(model=cfg.model, api_key=cfg.api_key, api_base=cfg.api_base)
        analyzer = Analyzer(llm=llm, cache=cache, language=cfg.language, concurrency=cfg.concurrency)

        wiki_data = await analyzer.analyze(project, on_progress=progress)

        graph = DependencyGraph.build_from_project(project)
        builder = WikiBuilder()
        wiki = builder.build(project, wiki_data, graph)

        proj["wiki"] = wiki
        proj["info"].status = "done"
        progress("Done!")

    except Exception as e:
        proj["info"].status = "error"
        proj["info"].error = str(e)
        proj["progress"].append(f"Error: {e}")
