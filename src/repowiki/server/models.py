"""pydantic models for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    path: str | None = None
    url: str | None = None
    language: str = "en"
    model: str | None = None
    api_key: str | None = None
    api_base: str | None = None
    protocol: str | None = None


class ProtocolCheckRequest(BaseModel):
    """Payload for pinging a gateway with the selected model before saving."""

    protocol: str | None = None
    api_base: str | None = None
    api_key: str | None = None
    model: str | None = None


class ProjectInfo(BaseModel):
    id: str
    name: str
    status: str = "pending"  # pending, scanning, done, error
    total_files: int = 0
    total_lines: int = 0
    error: str = ""


class ChatTurn(BaseModel):
    """one prior exchange in the conversation."""

    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    # prior turns, oldest first; the server threads them into the prompt so
    # follow-up questions have context
    history: list[ChatTurn] = Field(default_factory=list)


class FileReference(BaseModel):
    path: str
    line_start: int = 0
    line_end: int = 0
    snippet: str = ""
