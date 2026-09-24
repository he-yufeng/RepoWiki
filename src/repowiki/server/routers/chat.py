"""Q&A chat endpoint with RAG."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse

from repowiki.config import Config, resolve_model
from repowiki.server.app import get_projects
from repowiki.server.models import ChatRequest

router = APIRouter()


@router.post("/project/{project_id}/chat")
async def chat(
    project_id: str,
    req: ChatRequest,
    x_api_key: str | None = Header(None),
    x_api_protocol: str | None = Header(None),
    x_api_base: str | None = Header(None),
    x_model: str | None = Header(None),
):
    """SSE streaming chat response with RAG retrieval."""
    projects = get_projects()
    proj = projects.get(project_id)
    if not proj or not proj.get("project"):
        return {"error": "Project not ready"}

    project = proj["project"]

    # build RAG index if not cached (in memory first, then the on-disk cache
    # so a restarted server on an unchanged repo skips the rebuild). A cold
    # build tokenizes the whole repo, so keep it off the event loop.
    if "rag" not in proj:
        from repowiki.core.rag import load_or_build_index

        rag, _ = await asyncio.to_thread(load_or_build_index, project)
        proj["rag"] = rag
    else:
        rag = proj["rag"]

    # module cards carry the vocabulary raw code lacks: a paraphrased (or
    # Chinese) question with no lexical overlap against the chunks can still
    # reach the right files through the card match
    boost = None
    wiki = proj.get("wiki")
    if wiki is not None and getattr(wiki, "modules", None):
        if "module_index" not in proj:
            from repowiki.core.rag import ModuleIndex

            proj["module_index"] = ModuleIndex.from_modules(wiki.modules)
        boost = proj["module_index"].file_scores(req.question)

    # retrieve relevant chunks
    chunks = rag.retrieve(req.question, top_k=5, boost=boost)
    context_parts = []
    references = []
    for chunk in chunks:
        context_parts.append(
            f"### {chunk.file_path} (lines {chunk.line_start}-{chunk.line_end})\n"
            f"```\n{chunk.content}\n```"
        )
        references.append({
            "path": chunk.file_path,
            "line_start": chunk.line_start,
            "line_end": chunk.line_end,
            "snippet": chunk.content[:200],
        })

    context_text = "\n\n".join(context_parts)

    # get LLM config; the web UI sends its saved protocol/base/model as
    # headers so chat honours the settings form, not just the config file
    cfg = Config.load()
    if x_api_key:
        cfg.api_key = x_api_key
    if x_api_protocol:
        cfg.protocol = x_api_protocol
    if x_api_base:
        cfg.api_base = x_api_base
    if x_model:
        cfg.model = resolve_model(x_model)

    if not cfg.api_key:
        return {"error": "No API key configured"}

    from repowiki.llm.client import LLMClient
    from repowiki.llm.prompts import build_chat_prompt

    llm = LLMClient(
        model=cfg.model,
        api_key=cfg.api_key,
        api_base=cfg.api_base,
        protocol=cfg.protocol or None,
    )
    history = [{"role": t.role, "content": t.content} for t in req.history]
    messages = build_chat_prompt(req.question, context_text, cfg.language, history=history)

    async def event_stream():
        # send references first
        yield f"data: {json.dumps({'references': references})}\n\n"

        # stream the answer
        async for chunk in llm.stream(messages):
            yield f"data: {json.dumps({'content': chunk})}\n\n"

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
