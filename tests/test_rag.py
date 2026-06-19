"""Tests for the TF-IDF retrieval that powers `repowiki chat`."""

from __future__ import annotations

from repowiki.core.models import FileInfo, ProjectContext
from repowiki.core.rag import SimpleRAG, format_context


def _project(*files: tuple[str, str]) -> ProjectContext:
    return ProjectContext(
        name="demo",
        root="/demo",
        files=[
            FileInfo(path=path, size=len(content), language="python", content=content)
            for path, content in files
        ],
    )


def test_retrieve_ranks_relevant_file_first():
    # several files so TF-IDF is non-degenerate (a 2-doc corpus collapses idf to 0)
    project = _project(
        ("auth.py", "def login(user, password):\n    return verify_password(user, password)\n"),
        ("db.py", "def connect_database(url):\n    return create_engine(url)\n"),
        ("cache.py", "def get_cached(key):\n    return store.lookup(key)\n"),
        ("router.py", "def add_route(path, handler):\n    routes.append((path, handler))\n"),
        ("logging.py", "def log_event(name):\n    writer.emit(name)\n"),
    )
    rag = SimpleRAG()
    rag.index(project)
    results = rag.retrieve("how does password login work")
    assert results, "expected at least one relevant chunk"
    assert results[0].file_path == "auth.py"
    assert results[0].score > 0


def test_unrelated_query_returns_nothing():
    project = _project(("auth.py", "def login(user, password): ...\n"))
    rag = SimpleRAG()
    rag.index(project)
    # no token overlap -> cosine similarity 0 -> filtered out
    assert rag.retrieve("kubernetes helm chart deployment") == []


def test_empty_index_retrieve():
    rag = SimpleRAG()
    assert rag.retrieve("anything") == []


def test_index_skips_empty_files():
    project = _project(("empty.py", ""), ("real.py", "def f():\n    return 1\n"))
    rag = SimpleRAG()
    rag.index(project)
    assert all(c.file_path == "real.py" for c in rag.chunks)


def test_format_context():
    project = _project(("auth.py", "def login():\n    pass\n"))
    rag = SimpleRAG()
    rag.index(project)
    chunks = rag.retrieve("login")
    ctx = format_context(chunks)
    assert "auth.py" in ctx
    assert "```" in ctx
    assert "def login" in ctx


def test_format_context_empty():
    assert "no relevant code" in format_context([])
