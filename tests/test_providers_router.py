"""Endpoint tests for the protocol router: listing, check, discovery.

httpx and litellm's capability lookup are faked so no network is touched and
litellm's import cost is never paid here. The key-masking discipline is the
point of several tests: a raw credential must never leave the server.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

import httpx
from fastapi.testclient import TestClient

from repowiki.config import MODEL_ALIASES, MODEL_LABELS
from repowiki.core.cache import Cache
from repowiki.server import app as app_module
from repowiki.server.routers import providers as router_module

_KEY = "sk-sp-SECRET123"


def _client(monkeypatch, tmp_path):
    monkeypatch.setattr(app_module, "Cache", lambda: Cache(tmp_path / "cache.db"))
    return TestClient(app_module.create_app(static_dir=tmp_path / "missing"))


class _FakeResp:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json body")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=None)


class _FakeAsyncClient:
    """httpx.AsyncClient stand-in capturing the probe request."""

    last_url = ""
    last_headers: dict = {}
    post_resp = None

    def __init__(self, resp=None, exc=None):
        self._resp = resp
        self._exc = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, headers=None):
        if self._exc is not None:
            raise self._exc
        _FakeAsyncClient.last_url = url
        _FakeAsyncClient.last_headers = headers or {}
        return self._resp

    async def post(self, url, json=None, headers=None):
        if self._exc is not None:
            raise self._exc
        _FakeAsyncClient.last_url = url
        _FakeAsyncClient.last_headers = headers or {}
        return _FakeAsyncClient.post_resp or _FakeResp(200, {"id": "ping"})


def _patch_httpx(monkeypatch, resp=None, exc=None):
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda *a, **k: _FakeAsyncClient(resp=resp, exc=exc)
    )
    _FakeAsyncClient.last_url = ""
    _FakeAsyncClient.last_headers = {}
    _FakeAsyncClient.post_resp = None


def test_protocols_endpoint_lists_protocols(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        r = client.get("/api/protocols")
    assert r.status_code == 200
    protos = r.json()["protocols"]
    assert [p["id"] for p in protos] == ["chat_completions", "anthropic_messages"]
    # registry data only — no secrets leak into the listing
    assert all("api_key" not in p for p in protos)
    assert protos[0]["base_hint"]
    assert protos[0]["wire"]


def test_model_presets_endpoint_mirrors_the_aliases(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        r = client.get("/api/model-presets")
    assert r.status_code == 200
    presets = r.json()["presets"]
    # served from MODEL_ALIASES, so the picker cannot drift from the routing
    assert [p["id"] for p in presets] == list(MODEL_ALIASES)
    by_id = {p["id"]: p for p in presets}
    assert by_id["deepseek"]["model"] == MODEL_ALIASES["deepseek"]
    assert by_id["deepseek"]["label"] == MODEL_LABELS["deepseek"]
    # every alias carries a label, so the form never shows a bare id
    assert set(MODEL_LABELS) == set(MODEL_ALIASES)
    assert all(p["label"] for p in presets)


def test_check_requires_base_url(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        r = client.post(
            "/api/protocols/check",
            json={"protocol": "chat_completions", "api_key": _KEY, "model": "m"},
        )
    body = r.json()
    assert body["ok"] is False
    assert "Base URL" in (body["diagnosis"] or "")


def test_check_unknown_protocol(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        r = client.post(
            "/api/protocols/check", json={"protocol": "nope", "api_base": "https://gw"}
        )
    assert r.json()["ok"] is False


def test_check_requires_model(monkeypatch, tmp_path):
    # the check tests exactly one model, so it refuses to run without one
    with _client(monkeypatch, tmp_path) as client:
        r = client.post(
            "/api/protocols/check",
            json={"protocol": "chat_completions", "api_base": "https://gw/v1", "api_key": _KEY},
        )
    body = r.json()
    assert body["ok"] is False
    assert "model" in (body["diagnosis"] or "").lower()


def test_check_pings_selected_model_chat(monkeypatch, tmp_path):
    _patch_httpx(monkeypatch, resp=_FakeResp(200, {"data": []}))
    with _client(monkeypatch, tmp_path) as client:
        r = client.post(
            "/api/protocols/check",
            json={
                "protocol": "chat_completions",
                "api_base": "https://gw.example.com",
                "api_key": _KEY,
                "model": "qwen3.8-flash",
            },
        )
    body = r.json()
    assert body["ok"] is True
    # base normalised to the OpenAI-style /v1 convention
    assert body["base_url"] == "https://gw.example.com/v1"
    # only the selected model is tested, via a 1-token chat completion
    assert _FakeAsyncClient.last_url == "https://gw.example.com/v1/chat/completions"
    assert _FakeAsyncClient.last_headers.get("Authorization") == f"Bearer {_KEY}"
    # the raw key never appears in the response body
    assert body["masked_key"] == "sk-sp-***T123"
    assert _KEY not in r.text


def test_check_anthropic_pings_messages(monkeypatch, tmp_path):
    _patch_httpx(monkeypatch, resp=_FakeResp(200, {"data": []}))
    with _client(monkeypatch, tmp_path) as client:
        r = client.post(
            "/api/protocols/check",
            json={
                "protocol": "anthropic_messages",
                "api_base": "https://api.anthropic.com/v1",
                "api_key": "sk-ant-SECRET1",
                "model": "claude-x",
            },
        )
    body = r.json()
    assert body["ok"] is True
    # Anthropic-style base is a bare root (client appends /v1/messages)
    assert body["base_url"] == "https://api.anthropic.com"
    assert _FakeAsyncClient.last_url == "https://api.anthropic.com/v1/messages"
    assert _FakeAsyncClient.last_headers.get("x-api-key") == "sk-ant-SECRET1"


def test_check_unauthorized_diagnosis(monkeypatch, tmp_path):
    _patch_httpx(monkeypatch, resp=_FakeResp(200, {"data": []}))
    _FakeAsyncClient.post_resp = _FakeResp(401, {"error": "bad key"})
    with _client(monkeypatch, tmp_path) as client:
        r = client.post(
            "/api/protocols/check",
            json={
                "protocol": "chat_completions",
                "api_base": "https://gw/v1",
                "api_key": _KEY,
                "model": "m",
            },
        )
    body = r.json()
    assert body["ok"] is False
    assert body["status_code"] == 401
    assert "key" in (body["diagnosis"] or "").lower()


def test_check_redacts_key_from_transport_error(monkeypatch, tmp_path):
    _patch_httpx(monkeypatch, exc=httpx.ConnectError(f"unreachable with {_KEY}"))
    with _client(monkeypatch, tmp_path) as client:
        r = client.post(
            "/api/protocols/check",
            json={
                "protocol": "chat_completions",
                "api_base": "https://gw/v1",
                "api_key": _KEY,
                "model": "m",
            },
        )
    body = r.json()
    assert body["ok"] is False
    assert _KEY not in r.text
    assert _KEY not in body["diagnosis"]


def test_models_endpoint_flags_non_chat(monkeypatch, tmp_path):
    def fake_meta(model):
        chat = "image" not in model and "tts" not in model
        return {
            "mode": None,
            "max_input_tokens": 1000 if chat else None,
            "max_output_tokens": 2000 if chat else None,
            "input_cost_per_token": None,
            "output_cost_per_token": None,
            "metadata_source": "test",
        }

    monkeypatch.setattr(router_module, "model_metadata", fake_meta)
    payload = {"data": [{"id": "qwen3.8-flash"}, {"id": "wan2.7-image"}]}
    _patch_httpx(monkeypatch, resp=_FakeResp(200, payload))
    with _client(monkeypatch, tmp_path) as client:
        r = client.get(
            "/api/models",
            params={"protocol": "chat_completions", "api_base": "https://gw/v1"},
            headers={"x-api-key": _KEY},
        )
    body = r.json()
    assert body["discoverable"] is True
    assert body["count"] == 2
    by_id = {m["id"]: m for m in body["models"]}
    assert by_id["qwen3.8-flash"]["chat"] is True
    assert by_id["qwen3.8-flash"]["litellm_model"] == "openai/qwen3.8-flash"
    assert by_id["wan2.7-image"]["chat"] is False  # name hints a non-chat model
    assert "non-chat" in by_id["wan2.7-image"]["chat_reason"]


def test_models_endpoint_reports_no_list(monkeypatch, tmp_path):
    # Anthropic-compatible gateways often expose no models list at all
    _patch_httpx(monkeypatch, resp=_FakeResp(404, {"error": "no models"}))
    with _client(monkeypatch, tmp_path) as client:
        r = client.get(
            "/api/models",
            params={"protocol": "anthropic_messages", "api_base": "https://gw"},
            headers={"x-api-key": _KEY},
        )
    body = r.json()
    assert body["models"] == []
    assert body["discoverable"] is False
    assert body["status_code"] == 404
    assert _KEY not in r.text


def test_models_endpoint_requires_protocol_and_base(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        r = client.get("/api/models")
    body = r.json()
    assert body["models"] == []
    assert body["error"]


def test_models_endpoint_reports_transport_error(monkeypatch, tmp_path):
    _patch_httpx(monkeypatch, exc=httpx.ConnectError(f"down {_KEY}"))
    with _client(monkeypatch, tmp_path) as client:
        r = client.get(
            "/api/models",
            params={"protocol": "chat_completions", "api_base": "https://gw/v1"},
            headers={"x-api-key": _KEY},
        )
    body = r.json()
    assert body["models"] == []
    assert "error" in body
    assert _KEY not in r.text
