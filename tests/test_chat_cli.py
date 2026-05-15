"""Smoke test that the chat CLI command is wired up end-to-end."""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from repowiki.cli import cli


def test_chat_command_is_registered():
    result = CliRunner().invoke(cli, ["chat", "--help"])
    assert result.exit_code == 0
    assert "Ask questions about a codebase" in result.output
    assert "--model" in result.output
    assert "--top-k" in result.output


def test_simple_rag_indexes_and_retrieves(tmp_path):
    """RAG index built from a small project routes a relevant query
    to the right file. (Needs >=3 docs because the TF-IDF formula
    degenerates to zero IDF in 2-doc corpora.)"""
    from repowiki.core.models import FileInfo, ProjectContext
    from repowiki.core.rag import SimpleRAG

    bodies = {
        "auth.py": "def login(user, password):\n    return verify(user, password)\n",
        "db.py":   "def query(sql):\n    return run_sql_against_database(sql)\n",
        "ui.py":   "def render(template):\n    return html_engine.render(template)\n",
        "logs.py": "def write(message):\n    file_handle.append(message)\n",
    }
    files = [
        FileInfo(path=p, size=len(b), language="python",
                 lines=b.count("\n") + 1, preview=b, content=b)
        for p, b in bodies.items()
    ]
    project = ProjectContext(name="x", root="/tmp/x", files=files)
    rag = SimpleRAG()
    rag.index(project)

    hits = rag.retrieve("how does user login and password verify")
    assert hits, "expected at least one TF-IDF hit"
    assert hits[0].file_path == "auth.py"


def test_chat_requires_api_key(tmp_path, monkeypatch):
    """chat must refuse to start with no key configured rather than scanning."""
    # isolate from the user's real ~/.repowiki/config.json
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    for k in ("REPOWIKI_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(k, raising=False)

    sample = tmp_path / "proj"
    sample.mkdir()
    (sample / "main.py").write_text("print('hi')\n", encoding="utf-8")

    result = CliRunner().invoke(cli, ["chat", str(sample)])
    assert result.exit_code != 0
    assert "No API key" in result.output
