"""Q&A chat endpoint with RAG."""

from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse

from repowiki.config import Config
from repowiki.server.app import get_projects
from repowiki.server.models import ChatRequest

router = APIRouter()
logger = logging.getLogger(__name__)


def _sse_error(message: str) -> StreamingResponse:
    """return a one-shot SSE response carrying an error frame.

    Keeping the content-type stable means the frontend's existing stream
    parser handles the error path the same way it handles success, so the
    error always surfaces in the UI -- no more 500s that vanish into the
    fetch() catch.
    """
    async def _stream():
        yield f"data: {json.dumps({'error': message})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.post("/project/{project_id}/chat")
async def chat(project_id: str, req: ChatRequest, x_api_key: str | None = Header(None)):
    """SSE streaming chat response with RAG retrieval."""
    projects = get_projects()
    proj = projects.get(project_id)
    if not proj or not proj.get("project"):
        return _sse_error("Project not ready")

    project = proj["project"]

    cfg = Config.load()
    if x_api_key:
        cfg.api_key = x_api_key

    # The scan flow preheats ``proj["rag"]`` after analysis. If the preheat
    # task hasn't finished, try the on-disk index first; only fall back to
    # a fresh in-memory rebuild if there's no snapshot for this project
    # (e.g. the server restarted without re-scanning, or this is a brand
    # new project_id we somehow have in memory but never persisted).
    rag = proj.get("rag")
    if rag is None:
        from repowiki.core.rag import SimpleRAG
        from repowiki.core.rag_store import RagStore

        store = RagStore()
        try:
            await store.init()
            rag = await store.load(project_id)
        finally:
            await store.close()

        if rag is None:
            def _build() -> SimpleRAG:
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
            rag = await loop.run_in_executor(None, _build)
        proj["rag"] = rag

    # Retrieval is in-memory and cheap; keep it on the event loop.
    t_retrieve_start = time.monotonic()
    chunks = rag.retrieve(
        req.question,
        top_k=cfg.rag_top_k,
        min_score=cfg.rag_min_score,
    )
    retrieve_ms = (time.monotonic() - t_retrieve_start) * 1000.0
    context_parts = []
    references = []
    for chunk in chunks:
        context_parts.append(
            f"### {chunk.file_path} (lines {chunk.line_start}-{chunk.line_end})\n"
            f"```\n{chunk.content}\n```"
        )
        # Snippet is the first 50 lines (capped at ~4 KB) so the chat UI can
        # show a meaningful preview alongside the citation link. Previously
        # we sent the first 200 chars which often cut mid-token.
        snippet_lines = chunk.content.splitlines()[:50]
        snippet = "\n".join(snippet_lines)[:4096]
        references.append({
            "path": chunk.file_path,
            "line_start": chunk.line_start,
            "line_end": chunk.line_end,
            "snippet": snippet,
        })

    context_text = "\n\n".join(context_parts)

    logger.info(
        "chat project=%s q_len=%d retrieved=%d retrieve_ms=%.1f",
        project_id, len(req.question or ""), len(chunks), retrieve_ms,
    )

    if not cfg.api_key:
        return _sse_error(
            "No API key configured. Open Settings and add one, "
            "or set DEEPSEEK_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY."
        )

    from repowiki.llm.client import LLMClient, LLMError
    from repowiki.llm.prompts import build_chat_prompt

    llm = LLMClient(model=cfg.model, api_key=cfg.api_key, api_base=cfg.api_base)
    messages = build_chat_prompt(
        req.question, context_text, cfg.language, history=req.history,
    )

    async def event_stream():
        # send references first so the UI can render the citations panel
        # even if the stream is later cancelled or errors out mid-flight.
        yield f"data: {json.dumps({'references': references})}\n\n"

        t_stream_start = time.monotonic()
        try:
            agen = llm.stream(messages).__aiter__()
            while True:
                try:
                    # Cap the wait between provider chunks. When the LLM is
                    # mid-thought for a long time (Claude with thinking, or
                    # any slow first-token model) we periodically flush a
                    # SSE comment line so reverse proxies / gateways don't
                    # consider the connection idle and tear it down.
                    chunk = await asyncio.wait_for(agen.__anext__(), timeout=15.0)
                except asyncio.TimeoutError:
                    # `:` prefixed lines are SSE comments; the frontend
                    # parser ignores any line that doesn't start with
                    # ``data: ``. Browsers + nginx treat them as activity.
                    yield ": heartbeat\n\n"
                    continue
                except StopAsyncIteration:
                    break
                yield f"data: {json.dumps({'content': chunk})}\n\n"
        except LLMError as e:
            logger.warning("chat stream failed: %s", e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            stream_ms = (time.monotonic() - t_stream_start) * 1000.0
            logger.info(
                "chat done project=%s in=%d out=%d cost=%.4f stream_ms=%.0f",
                project_id,
                llm.total_input_tokens,
                llm.total_output_tokens,
                llm.total_cost,
                stream_ms,
            )

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
