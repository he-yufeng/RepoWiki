"""The chat router must thread request history into the LLM prompt."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")  # TestClient dependency

from fastapi.testclient import TestClient

from repowiki.core.cache import Cache
from repowiki.core.models import FileInfo, ProjectContext
from repowiki.core.rag import SimpleRAG
from repowiki.server import app as app_module


def _client(monkeypatch, tmp_path):
    # keep the lifespan cache out of the real home directory
    monkeypatch.setattr(app_module, "Cache", lambda: Cache(tmp_path / "cache.db"))
    return TestClient(app_module.create_app(static_dir=tmp_path / "missing"))


def _seed_project(monkeypatch) -> None:
    project = ProjectContext(
        name="demo",
        root="/demo",
        files=[
            FileInfo(
                path="auth.py",
                size=40,
                language="python",
                content="def login(user, password):\n    return check(user, password)\n",
            )
        ],
    )
    rag = SimpleRAG()
    rag.index(project)
    # seeding "rag" up front keeps the on-disk index cache out of this test
    monkeypatch.setitem(
        app_module._projects, "p1", {"project": project, "rag": rag}
    )


class StubLLM:
    def __init__(self, *args, **kwargs):
        pass

    async def stream(self, messages):
        StubLLM.captured = messages
        yield "stub answer"


def test_chat_router_threads_history_into_prompt(monkeypatch, tmp_path):
    _seed_project(monkeypatch)
    monkeypatch.setattr("repowiki.llm.client.LLMClient", StubLLM)

    with _client(monkeypatch, tmp_path) as client:
        resp = client.post(
            "/api/project/p1/chat",
            json={
                "question": "what does it return",
                "history": [
                    {"role": "user", "content": "where is login defined"},
                    {"role": "assistant", "content": "in auth.py line 1"},
                ],
            },
            headers={"x-api-key": "test-key"},
        )

    assert resp.status_code == 200
    msgs = StubLLM.captured
    assert [m["role"] for m in msgs] == ["system", "user", "assistant", "user"]
    assert msgs[1]["content"] == "where is login defined"
    assert msgs[2]["content"] == "in auth.py line 1"
    assert "what does it return" in msgs[-1]["content"]
    assert '"references"' in resp.text
    assert '"done": true' in resp.text


def test_chat_router_without_history_keeps_old_shape(monkeypatch, tmp_path):
    _seed_project(monkeypatch)
    monkeypatch.setattr("repowiki.llm.client.LLMClient", StubLLM)

    with _client(monkeypatch, tmp_path) as client:
        resp = client.post(
            "/api/project/p1/chat",
            json={"question": "where is login"},
            headers={"x-api-key": "test-key"},
        )

    assert resp.status_code == 200
    assert [m["role"] for m in StubLLM.captured] == ["system", "user"]
