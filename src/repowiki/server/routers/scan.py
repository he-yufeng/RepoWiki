"""scan and project management endpoints."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os

from fastapi import APIRouter, BackgroundTasks, Header
from fastapi.responses import StreamingResponse

from repowiki.config import Config, resolve_model
from repowiki.server.app import get_cache, get_projects
from repowiki.server.models import ProjectInfo, ScanRequest

router = APIRouter()


def _project_id_for(req: ScanRequest) -> str:
    """derive a stable 8-char project id from the source path or URL.

    Stability across server restarts is what lets the on-disk RAG snapshot
    (rag_store) actually pay off -- re-scanning the same target rebuilds
    the in-memory project but loads chunks from disk instead of re-
    tokenising. A random UUID would orphan every snapshot.
    """
    key = req.url or (os.path.abspath(req.path) if req.path else "")
    if not key:
        # nothing identifying provided; fall back to a one-shot hash so the
        # response still has an id, but the snapshot won't be reused.
        key = "anonymous"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:8]


@router.post("/scan", response_model=ProjectInfo)
async def start_scan(req: ScanRequest, background_tasks: BackgroundTasks,
                     x_api_key: str | None = Header(None)):
    project_id = _project_id_for(req)
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

        # Resolve `since` git ref into changed_paths so the analyzer can skip
        # untouched modules. GitHub URL scans are always full -- to mirror the
        # CLI behaviour and because we'd have to clone twice to diff anyway.
        changed_paths: set[str] | None = None
        if req.since and req.path:
            from repowiki.ingest.git_diff import changed_paths_since
            try:
                changed_paths = changed_paths_since(req.path, req.since)
                if changed_paths:
                    progress(f"Incremental: {len(changed_paths)} changed files since {req.since}")
                else:
                    progress(f"Incremental ({req.since}): no changes detected, full re-analysis")
                    changed_paths = None
            except Exception as e:
                progress(f"Incremental scan failed ({e}); falling back to full")
                changed_paths = None
        proj["changed_paths"] = changed_paths

        # analyze
        from repowiki.core.analyzer import Analyzer
        from repowiki.core.graph import DependencyGraph
        from repowiki.core.wiki_builder import WikiBuilder
        from repowiki.llm.client import LLMClient

        cache = get_cache()
        llm = LLMClient(model=cfg.model, api_key=cfg.api_key, api_base=cfg.api_base)
        analyzer = Analyzer(
            llm=llm,
            cache=cache,
            language=cfg.language,
            concurrency=cfg.concurrency,
            max_context_tokens=cfg.max_context_tokens,
            changed_paths=changed_paths,
        )

        # Build the graph once; pass PageRank to analyzer for the reading
        # guide and reuse the graph for the wiki builder's dependency page.
        graph = DependencyGraph.build_from_project(project)
        rankings = graph.rank_files()

        wiki_data = await analyzer.analyze(
            project, on_progress=progress, rankings=rankings,
        )

        builder = WikiBuilder()
        wiki = builder.build(project, wiki_data, graph)

        proj["wiki"] = wiki
        proj["info"].status = "done"

        # Preheat the chat RAG index in the background so the first chat
        # request doesn't pay the indexing cost on the request thread.
        # When a previously-saved index exists we reload it and only
        # re-chunk files that genuinely changed; otherwise we do the full
        # build. Wiki pages are always re-indexed because they're fresh
        # output from this run.
        async def _preheat_rag():
            from repowiki.core.rag import SimpleRAG, _fast_sha
            from repowiki.core.rag_store import RagStore

            store = RagStore()
            try:
                await store.init()
                rag = await store.load(project_id)

                if rag is None:
                    progress("Building chat index (no prior snapshot)…")
                    # No prior snapshot -- full build off the event loop.
                    def _build_from_scratch() -> SimpleRAG:
                        r = SimpleRAG(
                            k1=cfg.rag_bm25_k1,
                            b=cfg.rag_bm25_b,
                            max_chunk_lines=cfg.rag_chunk_max_lines,
                            soft_chunk_lines=cfg.rag_chunk_soft_lines,
                            overlap_lines=cfg.rag_chunk_overlap_lines,
                        )
                        r.index(project)
                        return r

                    loop = asyncio.get_event_loop()
                    rag = await loop.run_in_executor(None, _build_from_scratch)
                else:
                    progress(f"Reloaded chat index from snapshot ({len(rag.chunks)} chunks)")
                    # Incremental path: diff file hashes and only re-chunk
                    # what actually changed. We do this in an executor too
                    # because hashing every file's body is CPU work.
                    def _apply_diff(rag: SimpleRAG) -> SimpleRAG:
                        prior_paths = set(rag._file_sha.keys())
                        # Restrict to code-kind file paths; wiki/* paths are
                        # owned by index_wiki_pages and get rebuilt below.
                        prior_code_paths = {p for p in prior_paths if not p.startswith("wiki/")}

                        seen: set[str] = set()
                        for f in project.files:
                            text = f.content or f.preview
                            if not text:
                                continue
                            seen.add(f.path)
                            sha = _fast_sha(text)
                            if rag._file_sha.get(f.path) == sha:
                                continue  # unchanged
                            rag.upsert_file(
                                f.path, sha=sha, language=f.language,
                                text=text, kind="code", rebuild=False,
                            )

                        # Files that disappeared from the project drop out.
                        for stale in prior_code_paths - seen:
                            rag.remove_file(stale, rebuild=False)

                        rag.rebuild_global()
                        return rag

                    loop = asyncio.get_event_loop()
                    rag = await loop.run_in_executor(None, _apply_diff, rag)

                # Always refresh wiki chunks -- the markdown is regenerated
                # by this scan so the old slices are stale either way.
                if cfg.rag_index_wiki:
                    rag.index_wiki_pages(wiki.pages)

                await store.save(project_id, rag)
                proj["rag"] = rag
            finally:
                await store.close()

        asyncio.create_task(_preheat_rag())

        progress("Done!")

    except Exception as e:
        proj["info"].status = "error"
        proj["info"].error = str(e)
        proj["progress"].append(f"Error: {e}")
