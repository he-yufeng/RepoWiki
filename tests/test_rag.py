"""tests for repowiki.core.rag: tokenization and chunking."""

from __future__ import annotations

from repowiki.core.models import FileInfo, ProjectContext
from repowiki.core.rag import (
    SimpleRAG,
    _split_identifier,
    _split_into_chunks,
    _tokenize,
)


def test_split_identifier_camel_case():
    parts = _split_identifier("getUserById")
    assert "getuserbyid" in parts
    assert "get" in parts
    assert "user" in parts
    assert "by" in parts
    assert "id" in parts


def test_split_identifier_snake_case():
    parts = _split_identifier("is_authenticated_user")
    assert "is_authenticated_user" in parts
    assert "authenticated" in parts
    assert "user" in parts


def test_split_identifier_plain_word_only_yields_lowercase():
    parts = _split_identifier("hello")
    assert parts == ["hello"]


def test_tokenize_drops_stopwords_and_short_pieces():
    tokens = _tokenize("def hello_world(): return None")
    # `def`, `return`, `none` filtered as stopwords; one-char tokens dropped
    assert "def" not in tokens
    assert "return" not in tokens
    assert "none" not in tokens
    assert "hello_world" in tokens
    assert "hello" in tokens
    assert "world" in tokens


def test_tokenize_keeps_meaningful_identifiers():
    tokens = _tokenize("getUserById getOrderTotal")
    # both originals + their sub-words land in the bag
    assert "getuserbyid" in tokens
    assert "user" in tokens
    assert "order" in tokens
    assert "total" in tokens


def test_python_chunking_splits_at_def_boundaries():
    code = "\n".join(
        [
            "def first():",
            *["    pass"] * 25,  # 25 lines, plus the def line above -> 26
            "",
            "def second():",
            *["    return 1"] * 25,
            "",
            "def third():",
            *["    return 2"] * 25,
        ]
    )
    chunks = _split_into_chunks(code, "x.py", "python", soft_chunk_lines=10)

    # Three top-level defs should result in at least 3 chunks, each
    # *containing* one of the def lines (the def itself may not be on
    # line 1 of the chunk because of the overlap window).
    assert len(chunks) >= 3
    bodies = [c.content for c in chunks]
    assert sum("def first" in b for b in bodies) >= 1
    assert sum("def second" in b for b in bodies) >= 1
    assert sum("def third" in b for b in bodies) >= 1


def test_chunking_unknown_language_falls_back_to_blank_lines():
    code = "alpha\nbeta\n\ngamma\ndelta\nepsilon\n"
    chunks = _split_into_chunks(code, "x.txt", language="")
    # smoke: returns non-empty list and preserves all content
    assert len(chunks) >= 1
    rebuilt = "\n".join(c.content for c in chunks)
    assert "alpha" in rebuilt and "epsilon" in rebuilt


def test_chunk_line_numbers_are_1_based():
    code = "alpha\nbeta\ngamma\n"
    chunks = _split_into_chunks(code, "x.txt", language="")
    assert chunks[0].line_start == 1
    assert chunks[0].line_end >= 1


def test_simple_rag_retrieve_matches_camel_case_via_sub_word():
    """query 'user' should retrieve a chunk containing getUserById."""
    project = ProjectContext(
        name="t",
        root=".",
        files=[
            FileInfo(
                path="a.py",
                size=100,
                language="python",
                lines=3,
                content="def getUserById(uid):\n    return uid\n",
            ),
            FileInfo(
                path="b.py",
                size=100,
                language="python",
                lines=2,
                content="def compute():\n    return 42\n",
            ),
        ],
    )
    rag = SimpleRAG()
    rag.index(project)
    hits = rag.retrieve("user", top_k=2)
    assert hits, "expected at least one hit for 'user'"
    assert hits[0].file_path == "a.py"


def test_simple_rag_filters_zero_score_results():
    project = ProjectContext(
        name="t",
        root=".",
        files=[
            FileInfo(
                path="a.py",
                size=10,
                language="python",
                lines=1,
                content="alpha beta gamma",
            ),
        ],
    )
    rag = SimpleRAG()
    rag.index(project)
    hits = rag.retrieve("xyzzy_no_match_whatsoever", top_k=5)
    assert hits == []
