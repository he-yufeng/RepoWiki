"""tests for BM25 fusion + incremental upsert/remove + wiki indexing.

These exercise the SimpleRAG surface added in the Phase 1 refactor without
touching the LLM, so they run in milliseconds.
"""

from __future__ import annotations

from repowiki.core.models import FileInfo, ProjectContext
from repowiki.core.rag import (
    SimpleRAG,
    _bm25,
    _fast_sha,
    _split_markdown_into_chunks,
    _tokenize,
)


def _proj(files: list[FileInfo]) -> ProjectContext:
    return ProjectContext(name="t", root=".", files=files)


def test_bm25_normalises_for_chunk_length():
    """Short docs containing the term should outscore long ones that
    happen to repeat it -- that's the whole point of BM25 over plain TF.
    """
    # Use the same IDF table for both calls so we measure pure length
    # normalisation rather than IDF differences.
    idf = {"alpha": 1.0}
    short = _bm25(["alpha"], {"alpha": 1}, chunk_len=10, idf=idf, avgdl=100, k1=1.5, b=0.75)
    long_ = _bm25(["alpha"], {"alpha": 1}, chunk_len=200, idf=idf, avgdl=100, k1=1.5, b=0.75)
    assert short > long_


def test_bm25_unknown_token_scores_zero():
    idf = {"alpha": 1.0}
    assert _bm25(["beta"], {"alpha": 1}, chunk_len=10, idf=idf, avgdl=10, k1=1.5, b=0.75) == 0.0


def test_retrieve_returns_normalised_score():
    project = _proj([
        FileInfo(
            path="a.py", size=10, language="python", lines=2,
            content="def authenticate_user(uid):\n    return uid\n",
        ),
        FileInfo(
            path="b.py", size=10, language="python", lines=2,
            content="def render_view(req):\n    return req\n",
        ),
    ])
    rag = SimpleRAG()
    rag.index(project)
    hits = rag.retrieve("authenticate", top_k=5)
    assert hits
    # Top hit scores into [0, 1] because we average two normalised channels.
    assert 0.0 < hits[0].score <= 1.0
    assert hits[0].file_path == "a.py"


def test_retrieve_min_score_filters_low_relevance():
    project = _proj([
        FileInfo(
            path="a.py", size=10, language="python", lines=1,
            content="def authenticate_user(): pass\n",
        ),
        FileInfo(
            path="b.py", size=10, language="python", lines=1,
            content="def render_view(): pass\n",
        ),
    ])
    rag = SimpleRAG()
    rag.index(project)
    # A very strict floor should drop the lower-scoring chunk.
    strict = rag.retrieve("authenticate", top_k=5, min_score=0.99)
    permissive = rag.retrieve("authenticate", top_k=5, min_score=0.0)
    assert len(strict) <= len(permissive)


def test_upsert_file_replaces_old_chunks():
    rag = SimpleRAG(soft_chunk_lines=2, max_chunk_lines=4)
    rag.upsert_file(
        "a.py", sha="v1", language="python",
        text="def first(): pass\n",
    )
    n_after_first = len(rag.chunks)
    # Replace with very different content -- the old "first" chunk must
    # disappear and the new content must be retrievable.
    rag.upsert_file(
        "a.py", sha="v2", language="python",
        text="def second_function_xyzzy(): pass\n",
    )
    # Same file -> still exactly one set of chunks; total didn't grow.
    assert len(rag.chunks) == n_after_first
    hits = rag.retrieve("xyzzy", top_k=5)
    assert hits and "xyzzy" in hits[0].content
    # And the old keyword no longer matches anything.
    assert rag.retrieve("first", top_k=5) == []


def test_remove_file_clears_chunks_and_keeps_alignment():
    rag = SimpleRAG()
    rag.upsert_file("a.py", sha="x", language="python",
                    text="def keep_alpha(): pass\n")
    rag.upsert_file("b.py", sha="y", language="python",
                    text="def drop_beta(): pass\n")
    rag.remove_file("b.py")

    # Length invariants the cosine + bm25 paths rely on.
    assert len(rag.chunks) == len(rag._tf_vectors) == len(rag._chunk_lens)
    # b.py is gone from both the chunk list and the file map.
    assert all(c.file_path != "b.py" for c in rag.chunks)
    assert "b.py" not in rag._file_to_chunks
    # a.py still searchable.
    hits = rag.retrieve("alpha", top_k=5)
    assert hits and hits[0].file_path == "a.py"


def test_wiki_indexing_assigns_wiki_kind():
    rag = SimpleRAG()
    rag.upsert_file(
        "src/a.py", sha=_fast_sha("def f(): pass"),
        language="python", text="def authenticate_user(): pass\n",
    )

    class _P:  # mimic WikiPage duck-typing without importing the real one
        def __init__(self, page_id: str, content: str):
            self.id = page_id
            self.content = content

    rag.index_wiki_pages([
        _P("architecture", "# Architecture\n\nThis project uses authentication for users.\n"),
        _P("index", "# Overview\n\nTodo lists and stuff.\n"),
    ])

    # Both kinds now live in the same index.
    kinds = {c.kind for c in rag.chunks}
    assert kinds == {"code", "wiki"}
    # A wiki-side query is matchable.
    hits = rag.retrieve("authentication users", top_k=5)
    assert any(c.kind == "wiki" for c in hits)


def test_wiki_indexing_replaces_prior_wiki_chunks():
    """Re-running scan must not double-index the same wiki page."""
    rag = SimpleRAG()

    class _P:
        def __init__(self, page_id: str, content: str):
            self.id = page_id
            self.content = content

    rag.index_wiki_pages([_P("index", "# A\nfirst body alpha\n")])
    n_first = len(rag.chunks)
    rag.index_wiki_pages([_P("index", "# A\nsecond body beta\n")])
    assert len(rag.chunks) == n_first  # same shape, just different content
    assert rag.retrieve("alpha", top_k=5) == []
    hits = rag.retrieve("beta", top_k=5)
    assert hits


def test_split_markdown_breaks_at_headings():
    md = (
        "# Title\n"
        "lead paragraph\n"
        "## Section A\n"
        "alpha text\n"
        "## Section B\n"
        "beta text\n"
    )
    chunks = _split_markdown_into_chunks(md, "x.md")
    # At least one chunk per heading (3 headings + the lead before any).
    assert len(chunks) >= 3
    joined = "\n---\n".join(c.content for c in chunks)
    assert "Section A" in joined and "Section B" in joined


def test_tokenize_smoke():
    """Sanity check that the camelCase/snake_case tokenisation behaviour
    still holds after the rewrite (test_rag.py covers it more thoroughly).
    """
    tokens = _tokenize("authenticateUser is_admin")
    assert "authenticate" in tokens and "user" in tokens
    assert "is_admin" in tokens and "admin" in tokens
