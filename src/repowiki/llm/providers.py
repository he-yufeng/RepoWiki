"""Declarative registry of LLM wire protocols and model-capability helpers.

A gateway is described by the *protocol* it speaks (OpenAI-compatible chat
completions vs Anthropic-compatible messages), not by a vendor brand: the
same key + base URL can serve many models, and vendor registries forced
users to pick a brand before they could paste a URL. Keeping the registry
declarative means adding a protocol never touches call sites.

This module must stay importable without pulling in litellm: litellm's
import costs seconds, so zero-LLM paths (``repowiki map``, server boot,
``/api/protocols``) must not pay it. litellm is imported lazily inside the
capability helpers only.
"""

from __future__ import annotations

from dataclasses import dataclass

# Conservative output budget when litellm's catalog knows nothing about a
# model: big enough for real answers, small enough to stay cheap.
_FALLBACK_MAX_OUTPUT = 8192
# Never ask for less than the historical hard-coded budget, and never more
# than this even for models with huge output windows (keeps cost bounded).
_MIN_MAX_TOKENS = 4096
_CAP_MAX_TOKENS = 32768


@dataclass(frozen=True)
class Protocol:
    """A wire protocol a gateway can speak.

    ``litellm_prefix`` is prepended to a bare model id to form the litellm
    model string. ``models_path`` is appended to the normalized base URL to
    list models. ``base_has_v1`` records whether the base URL is expected to
    end in ``/v1`` (OpenAI-style) or to be a bare root (Anthropic-style, where
    the client appends ``/v1/messages`` itself). ``wire`` is a short, plain
    description of the request shape shown under the format picker.
    """

    id: str
    label: str
    wire: str
    litellm_prefix: str
    models_path: str
    base_hint: str
    auth_header: str
    base_has_v1: bool


PROTOCOLS: tuple[Protocol, ...] = (
    Protocol(
        id="chat_completions",
        label="OpenAI-compatible",
        wire="POST {base}/chat/completions · model list GET {base}/models",
        litellm_prefix="openai/",
        models_path="/models",
        base_hint="https://api.example.com/v1",
        auth_header="authorization",
        base_has_v1=True,
    ),
    Protocol(
        id="anthropic_messages",
        label="Anthropic-compatible",
        wire="POST {base}/v1/messages · most gateways expose no model list",
        litellm_prefix="anthropic/",
        models_path="/v1/models",
        base_hint="https://api.anthropic.com",
        auth_header="x-api-key",
        base_has_v1=False,
    ),
)


def list_protocols() -> list[Protocol]:
    """Return every supported protocol, in display order."""
    return list(PROTOCOLS)


def get_protocol(protocol_id: str) -> Protocol | None:
    """Look a protocol up by id, or None when unknown."""
    for protocol in PROTOCOLS:
        if protocol.id == protocol_id:
            return protocol
    return None


def normalize_base_url(base: str, protocol_id: str) -> str:
    """Normalise a user-pasted base URL to the protocol's convention.

    The #1 support ticket in every BYOK tool is ``/v1/v1`` or a missing
    ``/v1``: OpenAI-style gateways want the base to end in ``/v1`` while
    Anthropic-style ones want a bare root. Fix it here, once, for everyone.
    Unknown protocols pass the trimmed URL through untouched.
    """
    cleaned = (base or "").strip().rstrip("/")
    protocol = get_protocol(protocol_id)
    if protocol is None:
        return cleaned
    if protocol.base_has_v1:
        return cleaned if cleaned.endswith("/v1") else f"{cleaned}/v1"
    if cleaned.endswith("/v1"):
        return cleaned[: -len("/v1")].rstrip("/")
    return cleaned


def resolve_litellm_model(protocol_id: str, model_id: str) -> str:
    """Compose the litellm model string for a protocol + model id.

    A model id that already carries a litellm prefix (``dashscope/...`` from
    the config aliases, or anything else with a ``/``) is passed through so
    explicit native routing keeps working. Raises ValueError for an unknown
    protocol or an empty model id, since protocols have no default model.
    """
    protocol = get_protocol(protocol_id)
    if protocol is None:
        raise ValueError(f"unknown protocol: {protocol_id}")
    if not model_id:
        raise ValueError(f"protocol {protocol_id} has no default model; pick one")
    if "/" in model_id:
        return model_id
    return f"{protocol.litellm_prefix}{model_id}"


def mask_key(key: str) -> str:
    """Return a display-safe rendering of an API key (first 6 / last 4)."""
    if not key:
        return ""
    if len(key) <= 10:
        return "***"
    return f"{key[:6]}***{key[-4:]}"


def redact_secret(text: str, secret: str) -> str:
    """Strip a secret out of free-form text (error messages, logs).

    Mirrors the discipline used for GitHub tokens: a credential must never
    survive into a user-visible string, so replace it wholesale with ``***``.
    """
    if not secret:
        return text
    return text.replace(secret, "***")


def _load_litellm():
    """Import litellm on first use only (see module docstring)."""
    import litellm

    return litellm


def _catalog_info(model: str) -> tuple[dict | None, str]:
    """Fetch litellm catalog metadata for ``model``.

    Returns ``(info, source)`` where source is ``litellm_catalog`` for a
    direct hit, ``cross_prefix`` when the bare model name was found under a
    different provider prefix (OpenAI-compatible gateways reuse model names
    litellm only knows elsewhere, e.g. ``openai/qwen3.8-flash`` vs
    ``openrouter/qwen/qwen3.8-flash``), or ``(None, "unknown")``.

    The fallback walks litellm's catalog (~4k keys) once per model, which costs
    well under a millisecond each; a 260-model discovery list lands around
    0.1s, so no index is kept for it.
    """
    litellm = _load_litellm()
    try:
        return litellm.get_model_info(model), "litellm_catalog"
    except Exception:
        pass

    bare = model.split("/", 1)[1] if "/" in model else model
    for key in litellm.model_cost:
        if key == bare or key.endswith("/" + bare):
            try:
                return litellm.get_model_info(key), "cross_prefix"
            except Exception:
                continue
    return None, "unknown"


def model_metadata(model: str) -> dict:
    """Summarise capability metadata for ``model`` for API responses.

    Unknown numbers are reported as None rather than guessed, so callers
    can surface "unknown" honestly instead of fabricating precision.
    """
    info, source = _catalog_info(model)
    if not info:
        return {
            "max_input_tokens": None,
            "max_output_tokens": None,
            "input_cost_per_token": None,
            "output_cost_per_token": None,
            "mode": None,
            "metadata_source": "unknown",
        }
    return {
        "max_input_tokens": info.get("max_input_tokens"),
        "max_output_tokens": info.get("max_output_tokens"),
        "input_cost_per_token": info.get("input_cost_per_token"),
        "output_cost_per_token": info.get("output_cost_per_token"),
        "mode": info.get("mode"),
        "metadata_source": source,
    }


def suggest_max_tokens(model: str) -> int:
    """Derive a sane ``max_tokens`` budget from the model's output window.

    Replaces the historical hard-coded 4096, which silently truncated
    reasoning models whose thinking alone exceeds that budget. Falls back
    to a conservative default when the catalog knows nothing.
    """
    info, _ = _catalog_info(model)
    cap = (info or {}).get("max_output_tokens") or _FALLBACK_MAX_OUTPUT
    return max(_MIN_MAX_TOKENS, min(int(cap), _CAP_MAX_TOKENS))
