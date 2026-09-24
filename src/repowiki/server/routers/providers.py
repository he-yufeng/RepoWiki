"""Wire-protocol registry, connection check, and live model discovery.

These back the settings form: the frontend lists protocols, probes whether a
gateway can list its models, and validates credentials by pinging exactly the
model the user picked. Nothing here may import litellm at module load —
``/api/protocols`` and app boot must stay cheap, so litellm is only touched
lazily inside ``/api/models`` via the capability helpers.
"""

from __future__ import annotations

from fastapi import APIRouter, Header

from repowiki.config import MODEL_ALIASES, MODEL_LABELS
from repowiki.llm.providers import (
    Protocol,
    get_protocol,
    list_protocols,
    mask_key,
    model_metadata,
    normalize_base_url,
    redact_secret,
)
from repowiki.server.models import ProtocolCheckRequest

router = APIRouter()

# litellm "mode" values that mean a model cannot answer a chat turn.
_NON_CHAT_MODES = {
    "image_generation",
    "audio",
    "tts",
    "embedding",
    "embeddings",
    "rerank",
    "moderation",
}
# Substrings that hint a model is non-chat when litellm's catalog is silent.
# Deliberately conservative: only strong, unambiguous signals.
_NON_CHAT_HINTS = (
    "image",
    "tts",
    "realtime",
    "embedding",
    "rerank",
    "whisper",
    "dall-e",
    "stable-diffusion",
    "-audio",
    "speech",
)


def _protocol_payload(protocol: Protocol) -> dict:
    """Serialise a protocol for the settings form (registry data, no secrets)."""
    return {
        "id": protocol.id,
        "label": protocol.label,
        "wire": protocol.wire,
        "litellm_prefix": protocol.litellm_prefix,
        "models_path": protocol.models_path,
        "base_hint": protocol.base_hint,
    }


def _auth_headers(protocol: Protocol, api_key: str) -> dict:
    """Build the auth header the protocol's gateways expect."""
    if not api_key:
        return {}
    if protocol.auth_header == "x-api-key":
        return {"x-api-key": api_key}
    return {"Authorization": f"Bearer {api_key}"}


def _classify_chat(model_id: str, mode: str | None) -> tuple[bool, str]:
    """Decide whether a model is chat-capable, and say why we think so."""
    if mode is not None:
        if mode in _NON_CHAT_MODES:
            return False, f"litellm reports mode '{mode}'"
        return True, f"litellm reports mode '{mode}'"
    lowered = model_id.lower()
    for hint in _NON_CHAT_HINTS:
        if hint in lowered:
            return False, f"name suggests a non-chat model ('{hint}')"
    return True, "assumed chat-capable (not in litellm catalog)"


def _failure_diagnosis(status_code: int, url: str) -> str:
    """Translate a non-200 probe into an actionable, key-free message."""
    if status_code in (401, 403):
        return (
            f"Rejected the API key ({status_code}). Check the key, or that it "
            "is valid for this endpoint."
        )
    if status_code == 404:
        return (
            f"No endpoint at {url} (404). The Base URL, API format or model "
            "id may be wrong."
        )
    return f"Unexpected status {status_code} from {url}."


def _model_entry(entry: object, prefix: str) -> dict | None:
    """Build one form row from a models-list entry, or None if it has no id."""
    model_id = entry.get("id") if isinstance(entry, dict) else str(entry)
    if not model_id:
        return None
    litellm_model = f"{prefix}{model_id}"
    meta = model_metadata(litellm_model)
    chat, chat_reason = _classify_chat(model_id, meta.get("mode"))
    return {
        "id": model_id,
        "litellm_model": litellm_model,
        "chat": chat,
        "chat_reason": chat_reason,
        "mode": meta.get("mode"),
        "max_input_tokens": meta.get("max_input_tokens"),
        "max_output_tokens": meta.get("max_output_tokens"),
        "input_cost_per_token": meta.get("input_cost_per_token"),
        "output_cost_per_token": meta.get("output_cost_per_token"),
        "metadata_source": meta.get("metadata_source"),
    }


async def _ping_chat(
    base: str, protocol: Protocol, headers: dict, model: str
) -> tuple[int | None, str | None]:
    """Send a 1-token request to validate auth + connectivity for one model.

    Some Anthropic-compatible gateways (e.g. Alibaba Bailian's
    ``/apps/anthropic``) expose ``/v1/messages`` but no ``/v1/models``, so a
    models probe 404s even with a valid key. A minimal generation against the
    caller-supplied model is the only honest way to confirm the credential.
    """
    import httpx

    if protocol.id == "anthropic_messages":
        url = f"{base}/v1/messages"
    else:
        url = f"{base}/chat/completions"
    body = {
        "model": model,
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "ping"}],
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        return None, f"Could not reach {url}: {exc}"
    if resp.status_code == 200:
        return 200, None
    return resp.status_code, _failure_diagnosis(resp.status_code, url)


async def _fetch_models(base: str, models_path: str, headers: dict) -> tuple[list, int | None, str | None]:
    """Fetch and unwrap a gateway's models list.

    Returns ``(entries, status, error)``: on success ``error`` is None; on any
    failure ``entries`` is empty and ``error`` is a key-free message. The HTTP
    status lets callers tell "no models endpoint" (404) from "bad key" (401).
    """
    import httpx

    status: int | None = None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{base}{models_path}", headers=headers)
        status = resp.status_code
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:  # network / HTTP / JSON errors all become a message
        return [], status, str(exc)
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    if not isinstance(data, list):
        return [], status, "Unexpected models response shape."
    return data, status, None


@router.get("/protocols")
async def protocols_list() -> dict:
    """List every supported wire protocol for the settings form."""
    return {"protocols": [_protocol_payload(p) for p in list_protocols()]}


@router.get("/model-presets")
async def model_presets() -> dict:
    """List the curated model aliases the form offers as a no-gateway shortcut.

    A preset resolves to a vendor's native endpoint through ``MODEL_ALIASES``,
    so it needs neither a Base URL nor a protocol choice: it is the path a user
    takes when they only have a vendor key. Served from the same dict that does
    the routing, so the picker cannot drift from what the backend accepts.
    """
    return {
        "presets": [
            {"id": alias, "label": MODEL_LABELS.get(alias, alias), "model": target}
            for alias, target in MODEL_ALIASES.items()
        ]
    }


@router.post("/protocols/check")
async def check_protocol(req: ProtocolCheckRequest) -> dict:
    """Validate base URL + key by pinging the selected model only.

    A 1-token request against the caller's model is the honest test: it works
    on gateways with or without a models list. The key is never echoed back:
    only a masked form and a plain diagnosis.
    """
    protocol = get_protocol(req.protocol or "")
    verdict: dict = {
        "ok": False,
        "base_url": "",
        "status_code": None,
        "masked_key": mask_key(req.api_key or ""),
        "diagnosis": None,
    }
    if protocol is None:
        verdict["diagnosis"] = "Unknown API format."
        return verdict
    if not (req.api_base or "").strip():
        verdict["diagnosis"] = "A Base URL is required."
        return verdict
    if not (req.model or "").strip():
        verdict["diagnosis"] = "Select or enter a model first; only that model is tested."
        return verdict

    base = normalize_base_url(req.api_base or "", protocol.id)
    verdict["base_url"] = base
    headers = _auth_headers(protocol, req.api_key or "")
    status, diagnosis = await _ping_chat(base, protocol, headers, (req.model or "").strip())
    verdict["status_code"] = status
    if diagnosis is None:
        verdict["ok"] = True
        return verdict
    verdict["diagnosis"] = redact_secret(diagnosis, req.api_key or "")
    return verdict


@router.get("/models")
async def discover_models(
    protocol: str | None = None,
    api_base: str | None = None,
    x_api_key: str | None = Header(None),
) -> dict:
    """List the models an endpoint serves, merged with capability metadata.

    Combines the gateway's live models list with litellm's catalog (context
    window, output budget, cost, mode). Non-chat models are flagged so the
    form can disable them with a reason; unknown ones are reported honestly.
    ``discoverable`` is false when the gateway exposes no models list at all
    (common for Anthropic-compatible endpoints), so the form can switch to
    manual model entry instead of showing a scary error.
    """
    proto = get_protocol(protocol or "")
    if proto is None or not (api_base or "").strip():
        return {
            "models": [],
            "count": 0,
            "discoverable": False,
            "error": "A protocol and Base URL are required.",
        }

    base = normalize_base_url(api_base or "", proto.id)
    headers = _auth_headers(proto, x_api_key or "")
    data, status, error = await _fetch_models(base, proto.models_path, headers)
    if error:
        return {
            "models": [],
            "count": 0,
            "discoverable": False,
            "status_code": status,
            "error": redact_secret(error, x_api_key or ""),
        }

    models = [m for m in (_model_entry(e, proto.litellm_prefix) for e in data) if m is not None]
    return {"models": models, "count": len(models), "discoverable": True}
