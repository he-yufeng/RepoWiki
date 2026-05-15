"""Config + alias resolution tests."""
import os
from pathlib import Path

import pytest

from repowiki.config import MODEL_ALIASES, Config, resolve_model


def test_alias_resolves_known_alias():
    assert resolve_model("opus") == MODEL_ALIASES["opus"]
    assert resolve_model("deepseek").startswith("deepseek/")


def test_alias_passes_through_unknown():
    assert resolve_model("foo/bar-baz") == "foo/bar-baz"
    assert resolve_model("anthropic/claude-something-new") == "anthropic/claude-something-new"


def test_aliases_have_provider_prefix():
    """every alias should map to a provider/model litellm can route."""
    for alias, target in MODEL_ALIASES.items():
        assert "/" in target, f"alias {alias!r} -> {target!r} missing provider prefix"


def test_config_load_reads_env(monkeypatch, tmp_path):
    # isolate from real ~/.repowiki
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("REPOWIKI_MODEL", "claude")
    monkeypatch.setenv("REPOWIKI_API_KEY", "test-key-123")

    cfg = Config.load()
    assert cfg.api_key == "test-key-123"
    # alias gets resolved on load
    assert cfg.model == MODEL_ALIASES["claude"]


def test_config_falls_back_to_provider_env(monkeypatch, tmp_path):
    monkeypatch.delenv("REPOWIKI_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-fallback")

    cfg = Config.load()
    assert cfg.api_key == "ds-fallback"
