"""Q&A chat endpoint with RAG."""

from __future__ import annotations

import json

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse

from repowiki.config import Config
from repowiki.server.app import get_projects
from repowiki.server.models import ChatRequest

router = APIRouter()


@router.post("/project/{project_id}/chat")
async def chat(project_id: str, req: ChatRequest, x_api_key: str | None = Header(None)):
    """SSE streaming chat response with RAG retrieval."""
    projects = get_projects()
    proj = projects.get(project_id)
    if not proj or not proj.get("project"):
        return {"error": "Project not ready"}

    project = proj["project"]

    # build RAG index if not cached
    if "rag" not in proj:
        from repowiki.core.rag import SimpleRAG
        rag = SimpleRAG()
        rag.index(project)
        proj["rag"] = rag
    else:
        rag = proj["rag"]

    # retrieve relevant chunks
    chunks = rag.retrieve(req.question, top_k=5)
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

    # get LLM config
    cfg = Config.load()
    if x_api_key:
        cfg.api_key = x_api_key

    if not cfg.api_key:
        return {"error": "No API key configured"}

    from repowiki.llm.client import LLMClient
    from repowiki.llm.prompts import build_chat_prompt

    llm = LLMClient(model=cfg.model, api_key=cfg.api_key, api_base=cfg.api_base)
    messages = build_chat_prompt(req.question, context_text, cfg.language)

    async def event_stream():
        # send references first
        yield f"data: {json.dumps({'references': references})}\n\n"

        # stream the answer
        async for chunk in llm.stream(messages):
            yield f"data: {json.dumps({'content': chunk})}\n\n"

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
