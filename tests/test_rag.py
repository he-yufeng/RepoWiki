"""Tests for the TF-IDF retrieval that powers `repowiki chat`."""

from __future__ import annotations

from types import SimpleNamespace

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


def _module_project() -> ProjectContext:
    return _project(
        ("storage.py", "def save_records(records):\n    write_json(records)\n"),
        ("cli.py", "def main():\n    parse_args()\n"),
        ("models.py", "class Record:\n    pass\n"),
        ("dates.py", "def parse_day(text):\n    return text\n"),
        ("views.py", "def render_page(page):\n    return page\n"),
    )


def test_cjk_question_tokenizes_to_bigrams():
    from repowiki.core.rag import _tokenize

    assert _tokenize("存储") == ["存储"]
    assert "储在" in _tokenize("存储在哪")


def test_module_boost_surfaces_zero_overlap_file():
    # the question shares no vocabulary with storage.py's code; only the
    # module card's Chinese description can bridge it
    from repowiki.core.rag import ModuleIndex

    rag = SimpleRAG()
    rag.index(_module_project())
    assert rag.retrieve("数据怎么安全地存到磁盘上") == []

    modules = [
        SimpleNamespace(
            name="persistence",
            purpose="把数据安全地写入磁盘",
            description="存储与崩溃安全",
            key_concepts=[],
            files=[SimpleNamespace(path="storage.py", purpose="磁盘存储", key_symbols=[])],
        )
    ]
    boost = ModuleIndex.from_modules(modules).file_scores("数据怎么安全地存到磁盘上")
    assert boost.get("storage.py", 0) > 0
    results = rag.retrieve("数据怎么安全地存到磁盘上", boost=boost)
    assert results and results[0].file_path == "storage.py"


def test_boost_never_displaces_lexical_hits():
    # a strong card match for another file must not push a direct lexical hit
    # out of the list: the card channel fills gaps, it does not reorder them away
    from repowiki.core.rag import ModuleIndex

    rag = SimpleRAG()
    rag.index(_module_project())
    plain = rag.retrieve("how are records saved with write_json")
    assert plain and plain[0].file_path == "storage.py"

    modules = [
        SimpleNamespace(
            name="interface",
            purpose="record saving entry points and helpers",
            description="save records write json entry",
            key_concepts=[],
            files=[SimpleNamespace(path="cli.py", purpose="record saving entry", key_symbols=[])],
        )
    ]
    boost = ModuleIndex.from_modules(modules).file_scores("how are records saved with write_json")
    boosted = rag.retrieve("how are records saved with write_json", boost=boost)
    assert boosted and boosted[0].file_path == "storage.py"


def test_module_index_empty_without_cards():
    from repowiki.core.rag import ModuleIndex

    idx = ModuleIndex.from_modules([])
    assert idx.file_scores("anything") == {}
