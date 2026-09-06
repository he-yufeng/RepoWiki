"""litellm must stay out of sys.modules until an LLM call is actually needed.

litellm's import costs seconds (and used to hang on 3.14), so the zero-LLM
paths (map, scan help, exports, the server) must not pay it. Probes run in
subprocesses because the pytest process itself imports litellm via other tests.
"""

import subprocess
import sys
import textwrap

import pytest


def _probe(code: str):
    proc = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr


def test_package_cli_and_analyzer_imports_stay_litellm_free():
    _probe(
        """
        import sys
        import repowiki
        import repowiki.cli
        from repowiki.core.analyzer import Analyzer  # the LLM pipeline module
        assert "litellm" not in sys.modules
        """
    )


def test_map_command_stays_litellm_free(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("from b import f\n\ndef g(): ...\n")
    (repo / "b.py").write_text("def f(): ...\n")
    _probe(
        f"""
        import sys
        from click.testing import CliRunner
        from repowiki.cli import cli
        r = CliRunner().invoke(cli, ["map", {str(repo)!r}])
        assert r.exit_code == 0, r.output
        assert "litellm" not in sys.modules
        """
    )


def test_scan_help_stays_litellm_free():
    _probe(
        """
        import sys
        from click.testing import CliRunner
        from repowiki.cli import cli
        r = CliRunner().invoke(cli, ["scan", "--help"])
        assert r.exit_code == 0, r.output
        assert "litellm" not in sys.modules
        """
    )


def test_server_app_import_stays_litellm_free():
    pytest.importorskip("fastapi")
    _probe(
        """
        import sys
        import repowiki.server.app
        assert "litellm" not in sys.modules
        """
    )


def test_llm_client_construction_imports_litellm():
    _probe(
        """
        import sys
        from repowiki.llm.client import LLMClient
        assert "litellm" not in sys.modules  # module import alone stays cheap
        LLMClient(model="gpt-4o-mini")
        assert "litellm" in sys.modules
        """
    )
