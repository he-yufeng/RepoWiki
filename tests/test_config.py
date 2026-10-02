"""Model aliases and vendor endpoint defaults."""

from __future__ import annotations

import json

import pytest

from repowiki import config as cfgmod
from repowiki.config import Config, resolve_model


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch, tmp_path):
    monkeypatch.setattr(cfgmod, "_CONFIG_FILE", tmp_path / "config.json")
    for var in (
        "REPOWIKI_MODEL",
        "REPOWIKI_API_KEY",
        "REPOWIKI_API_BASE",
        "REPOWIKI_LANG",
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)
    yield


def test_mimo_alias_resolves():
    assert resolve_model("mimo") == "openai/mimo-v2.6-flash"
    assert resolve_model("mimo-pro") == "openai/mimo-v2.6-pro"


def test_mimo_gets_vendor_endpoint(monkeypatch):
    monkeypatch.setenv("REPOWIKI_MODEL", "mimo")
    cfg = Config.load()
    assert cfg.model == "openai/mimo-v2.6-flash"
    assert cfg.api_base == "https://api.xiaomimimo.com/v1"


def test_user_base_url_wins_over_default(monkeypatch):
    monkeypatch.setenv("REPOWIKI_MODEL", "mimo")
    monkeypatch.setenv("REPOWIKI_API_BASE", "https://proxy.example.com/v1")
    cfg = Config.load()
    assert cfg.api_base == "https://proxy.example.com/v1"


def test_config_file_base_url_wins_over_default(tmp_path):
    (tmp_path / "config.json").write_text(
        json.dumps({"model": "mimo", "api_base": "https://proxy.example.com/v1"})
    )
    cfg = Config.load()
    assert cfg.api_base == "https://proxy.example.com/v1"


def test_other_models_get_no_default_base(monkeypatch):
    monkeypatch.setenv("REPOWIKI_MODEL", "deepseek")
    cfg = Config.load()
    assert cfg.api_base == ""


def test_vendor_aliases_resolve():
    assert resolve_model("qwen") == "openai/qwen3.7-plus"
    assert resolve_model("kimi") == "openai/kimi-k3"
    assert resolve_model("glm") == "openai/glm-5.3"
    assert resolve_model("minimax") == "openai/MiniMax-M3"


@pytest.mark.parametrize(
    "alias, base",
    [
        ("qwen", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        ("kimi", "https://api.moonshot.ai/v1"),
        ("glm", "https://open.bigmodel.cn/api/paas/v4"),
        ("minimax", "https://api.minimax.cn/v1"),
    ],
)
def test_vendor_aliases_get_endpoints(monkeypatch, alias, base):
    monkeypatch.setenv("REPOWIKI_MODEL", alias)
    cfg = Config.load()
    assert cfg.api_base == base


def test_max_tokens_round_trip(tmp_path):
    cfg = Config()
    cfg.max_tokens = 8192
    cfg.save()
    assert Config.load().max_tokens == 8192
