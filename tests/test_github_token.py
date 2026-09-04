"""GitHub token support for private-repo ingestion."""

from __future__ import annotations

import subprocess

import pytest

from repowiki.ingest import github as gh


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(gh, "_CLONE_DIR", tmp_path / "repos")
    yield


def test_token_used_for_github_clone(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
    captured = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = argv

        class R:
            returncode = 0
            stderr = ""

        return R()

    monkeypatch.setattr(gh.subprocess, "run", fake_run)
    url, token = gh._authenticated_clone_url("https://github.com/acme/private-repo")
    assert token == "secret-token"
    assert url == "https://x-access-token:secret-token@github.com/acme/private-repo.git"


def test_token_not_used_for_gitlab(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
    url, token = gh._authenticated_clone_url("https://gitlab.com/acme/private-repo")
    assert token is None
    assert url == "https://gitlab.com/acme/private-repo.git"


def test_no_token_in_env(monkeypatch):
    url, token = gh._authenticated_clone_url("https://github.com/acme/private-repo")
    assert token is None
    assert url == "https://github.com/acme/private-repo.git"


def test_gh_token_env_alias(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "alias-token")
    _, token = gh._authenticated_clone_url("https://github.com/acme/repo")
    assert token == "alias-token"


def test_token_never_leaks_into_errors(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
    err = subprocess.CalledProcessError(
        128,
        ["git", "clone"],
        stderr="fatal: Authentication failed for 'https://x-access-token:secret-token@github.com/acme/private-repo.git'",
    )
    monkeypatch.setattr(gh.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(err))

    with pytest.raises(RuntimeError) as exc_info:
        gh.ingest_github("https://github.com/acme/private-repo")

    assert "secret-token" not in str(exc_info.value)
    assert "***" in str(exc_info.value)


def test_timeout_error_uses_display_url(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
    monkeypatch.setattr(
        gh.subprocess,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(subprocess.TimeoutExpired(["git"], 120)),
    )

    with pytest.raises(RuntimeError) as exc_info:
        gh.ingest_github("https://github.com/acme/private-repo")

    assert "secret-token" not in str(exc_info.value)
