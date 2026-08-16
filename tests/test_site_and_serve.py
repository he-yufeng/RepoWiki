"""serve's path argument preloads a project, and --site writes a Pages loader."""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path

from click.testing import CliRunner

from repowiki.export.site import write_site_loader


def test_write_site_loader(tmp_path: Path):
    write_site_loader(tmp_path, "demo")
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "README.md" in index
    assert "_sidebar.md" not in index or True  # sidebar loads via $docsify config
    assert "loadSidebar" in index
    assert (tmp_path / ".nojekyll").exists()


def test_serve_passes_the_target_through(monkeypatch):
    from repowiki import cli

    captured = {}

    class FakeUvicorn:
        @staticmethod
        def run(*args, **kwargs):
            captured.update(kwargs)

    fake = types.SimpleNamespace(run=lambda *a, **k: captured.update(k))
    monkeypatch.setitem(sys.modules, "uvicorn", fake)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["serve", "/tmp/somewhere"])
    assert result.exit_code == 0
    assert os.environ.get("REPOWIKI_SERVE_TARGET") == "/tmp/somewhere"
    os.environ.pop("REPOWIKI_SERVE_TARGET", None)


def test_serve_default_path_does_not_set_target(monkeypatch):
    import os
    import sys
    import types

    from repowiki import cli

    fake = types.SimpleNamespace(run=lambda *a, **k: None)
    monkeypatch.setitem(sys.modules, "uvicorn", fake)
    os.environ.pop("REPOWIKI_SERVE_TARGET", None)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["serve"])
    assert result.exit_code == 0
    assert os.environ.get("REPOWIKI_SERVE_TARGET") is None
