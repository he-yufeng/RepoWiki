"""Unit tests for the wire-protocol registry and model-capability helpers.

litellm is faked so these stay fast and never touch the network or pay
litellm's multi-second import. The lazy-import contract itself is covered by
test_lazy_litellm.py.
"""

from __future__ import annotations

import pytest

from repowiki.llm import providers


class _FakeLitellm:
    """Stand-in exposing just the two attributes the helpers rely on."""

    def __init__(self, catalog: dict):
        self._catalog = catalog
        self.model_cost = {key: {} for key in catalog}

    def get_model_info(self, model: str):
        if model in self._catalog:
            return self._catalog[model]
        raise KeyError(model)


@pytest.fixture
def fake_catalog(monkeypatch):
    catalog = {
        "openrouter/qwen/qwen3.8-flash": {
            "max_input_tokens": 1000000,
            "max_output_tokens": 131072,
            "input_cost_per_token": 1.5e-07,
            "output_cost_per_token": 4.7e-07,
            "mode": "chat",
        },
        "openai/gpt-5.4": {
            "max_input_tokens": 1050000,
            "max_output_tokens": 128000,
            "mode": "chat",
        },
        "openai/tiny": {"max_output_tokens": 1000, "mode": "chat"},
    }
    monkeypatch.setattr(providers, "_load_litellm", lambda: _FakeLitellm(catalog))
    return catalog


def test_registry_is_well_formed():
    ids = [p.id for p in providers.PROTOCOLS]
    assert ids == ["chat_completions", "anthropic_messages"]
    for p in providers.PROTOCOLS:
        assert p.label and p.wire and p.litellm_prefix and p.models_path and p.base_hint
    chat = providers.get_protocol("chat_completions")
    assert chat.base_has_v1 is True
    assert chat.auth_header == "authorization"
    assert chat.models_path == "/models"
    anth = providers.get_protocol("anthropic_messages")
    assert anth.base_has_v1 is False
    assert anth.auth_header == "x-api-key"
    assert anth.models_path == "/v1/models"


def test_get_protocol_unknown():
    assert providers.get_protocol("nope") is None


@pytest.mark.parametrize(
    ("base", "protocol", "expected"),
    [
        ("https://gw.example.com", "chat_completions", "https://gw.example.com/v1"),
        ("https://gw.example.com/v1", "chat_completions", "https://gw.example.com/v1"),
        ("https://gw.example.com/v1/", "chat_completions", "https://gw.example.com/v1"),
        ("https://gw.example.com/compatible-mode", "chat_completions",
         "https://gw.example.com/compatible-mode/v1"),
        ("https://gw.example.com/compatible-mode/v1", "chat_completions",
         "https://gw.example.com/compatible-mode/v1"),
        ("https://api.anthropic.com/v1", "anthropic_messages", "https://api.anthropic.com"),
        ("https://api.anthropic.com", "anthropic_messages", "https://api.anthropic.com"),
        ("https://gw.example.com/v1/", "anthropic_messages", "https://gw.example.com"),
        ("https://gw.example.com/v1", "nope", "https://gw.example.com/v1"),
    ],
)
def test_normalize_base_url(base, protocol, expected):
    assert providers.normalize_base_url(base, protocol) == expected


def test_resolve_litellm_model():
    assert (
        providers.resolve_litellm_model("chat_completions", "qwen3.8-flash")
        == "openai/qwen3.8-flash"
    )
    assert (
        providers.resolve_litellm_model("anthropic_messages", "claude-x")
        == "anthropic/claude-x"
    )
    # an already-prefixed id (config aliases like dashscope/...) passes through
    assert providers.resolve_litellm_model("chat_completions", "dashscope/qwen") == "dashscope/qwen"
    with pytest.raises(ValueError):
        providers.resolve_litellm_model("nope", "m")
    with pytest.raises(ValueError):
        providers.resolve_litellm_model("chat_completions", "")


def test_mask_key():
    assert providers.mask_key("") == ""
    assert providers.mask_key("short") == "***"
    masked = providers.mask_key("sk-sp-SECRET123")
    assert masked == "sk-sp-***T123"
    assert "SECRET" not in masked


def test_redact_secret():
    assert providers.redact_secret("boom sk-sp-X", "sk-sp-X") == "boom ***"
    assert providers.redact_secret("no secret here", "") == "no secret here"


def test_suggest_max_tokens_direct_hit(fake_catalog):
    # a 128000 output window is clamped to the 32768 ceiling
    assert providers.suggest_max_tokens("openai/gpt-5.4") == 32768


def test_suggest_max_tokens_cross_prefix(fake_catalog):
    # openai/qwen3.8-flash misses directly but matches openrouter/qwen/...
    assert providers.suggest_max_tokens("openai/qwen3.8-flash") == 32768


def test_suggest_max_tokens_unknown_falls_back(fake_catalog):
    assert providers.suggest_max_tokens("openai/nope-xyz") == 8192


def test_suggest_max_tokens_never_below_floor(fake_catalog):
    # a 1000-token output window is raised to the 4096 historical floor
    assert providers.suggest_max_tokens("openai/tiny") == 4096


def test_model_metadata_cross_prefix_source(fake_catalog):
    meta = providers.model_metadata("openai/qwen3.8-flash")
    assert meta["metadata_source"] == "cross_prefix"
    assert meta["max_output_tokens"] == 131072
    assert meta["mode"] == "chat"


def test_model_metadata_unknown(fake_catalog):
    meta = providers.model_metadata("openai/nope-xyz")
    assert meta["metadata_source"] == "unknown"
    assert meta["max_output_tokens"] is None
    assert meta["mode"] is None


def test_model_metadata_matches_a_nested_bare_name(fake_catalog):
    # the suffix index must still find a name litellm knows two segments deep
    meta = providers.model_metadata("openai/qwen/qwen3.8-flash")
    assert meta["metadata_source"] == "cross_prefix"
    assert meta["max_output_tokens"] == 131072


def test_model_metadata_never_matches_a_partial_name(fake_catalog):
    # "flash" is a segment of a catalog key but not a whole bare name
    assert providers.model_metadata("openai/flash")["metadata_source"] == "unknown"


def test_llm_client_resolves_model_and_base_per_protocol(monkeypatch):
    from repowiki.llm import client as client_module

    monkeypatch.setattr(client_module, "_load_litellm", lambda: object())
    llm = client_module.LLMClient(
        model="qwen3.8-flash",
        api_key="k",
        api_base="https://gw.example.com",
        protocol="chat_completions",
    )
    assert llm.model == "openai/qwen3.8-flash"
    assert llm.api_base == "https://gw.example.com/v1"

    llm = client_module.LLMClient(
        model="claude-x", api_key="k", api_base="https://gw/v1", protocol="anthropic_messages"
    )
    assert llm.model == "anthropic/claude-x"
    assert llm.api_base == "https://gw"

    # no protocol: legacy pass-through so config aliases keep working
    llm = client_module.LLMClient(model="dashscope/qwen", api_base="https://gw/x")
    assert llm.model == "dashscope/qwen"
    assert llm.api_base == "https://gw/x"


def test_cli_apply_protocol_precedence():
    import click

    from repowiki.cli import _apply_protocol
    from repowiki.config import Config

    cfg = Config()
    _apply_protocol(cfg, "https://gw.example/v1", "chat_completions")
    assert cfg.api_base == "https://gw.example/v1"
    assert cfg.protocol == "chat_completions"

    cfg = Config()
    _apply_protocol(cfg, None, None)  # nothing supplied: config file wins
    assert cfg.api_base == ""
    assert cfg.protocol == ""

    with pytest.raises(click.UsageError):
        _apply_protocol(Config(), None, "nope")


def test_scan_request_carries_protocol_channel():
    from repowiki.server.models import ScanRequest

    req = ScanRequest(path=".", api_base="https://gw/v1", protocol="chat_completions")
    assert req.api_base == "https://gw/v1"
    assert req.protocol == "chat_completions"
