"""On-disk persistence of the TF-IDF index and honest invalidation."""

from __future__ import annotations

from repowiki.core.models import FileInfo, ProjectContext
from repowiki.core.rag import (
    SimpleRAG,
    index_fingerprint,
    load_or_build_index,
)


def _project(*files: tuple[str, str], root: str = "/demo") -> ProjectContext:
    return ProjectContext(
        name="demo",
        root=root,
        files=[
            FileInfo(path=path, size=len(content), language="python", content=content)
            for path, content in files
        ],
    )


def test_index_round_trip(tmp_path):
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

    path = tmp_path / "idx.json"
    rag.save_index(path)
    loaded = SimpleRAG.load_index(path)

    assert loaded is not None
    assert loaded.chunks == rag.chunks
    before = [c.file_path for c in rag.retrieve("password login")]
    after = [c.file_path for c in loaded.retrieve("password login")]
    assert before == after == ["auth.py"]


def test_load_or_build_hits_cache_when_repo_unchanged(tmp_path):
    project = _project(("a.py", "def login():\n    return 1\n"))
    rag1, hit1 = load_or_build_index(project, index_dir=tmp_path)
    assert not hit1

    rag2, hit2 = load_or_build_index(project, index_dir=tmp_path)
    assert hit2
    assert [c.file_path for c in rag2.chunks] == [c.file_path for c in rag1.chunks]


def test_content_change_invalidates_the_saved_index(tmp_path):
    project = _project(("a.py", "def login():\n    return 1\n"))
    _, hit1 = load_or_build_index(project, index_dir=tmp_path)
    assert not hit1

    changed = _project(("a.py", "def login():\n    return 2\n"))
    _, hit2 = load_or_build_index(changed, index_dir=tmp_path)
    assert not hit2


def test_file_set_change_invalidates_the_saved_index(tmp_path):
    project = _project(("a.py", "def login():\n    return 1\n"))
    load_or_build_index(project, index_dir=tmp_path)

    grown = _project(
        ("a.py", "def login():\n    return 1\n"),
        ("b.py", "def logout():\n    return 2\n"),
    )
    _, hit = load_or_build_index(grown, index_dir=tmp_path)
    assert not hit


def test_fingerprint_depends_on_repo_root(tmp_path):
    project = _project(("a.py", "def login():\n    return 1\n"), root="/demo")
    elsewhere = _project(("a.py", "def login():\n    return 1\n"), root="/other")
    assert index_fingerprint(project) != index_fingerprint(elsewhere)


def test_corrupt_index_file_is_a_cache_miss(tmp_path):
    project = _project(("a.py", "def login():\n    return 1\n"))
    path = tmp_path / f"{index_fingerprint(project)}.json"
    path.write_text("{ not json", encoding="utf-8")

    rag, hit = load_or_build_index(project, index_dir=tmp_path)
    assert not hit
    assert rag.chunks
    # and the corrupt file got replaced with a valid one
    assert SimpleRAG.load_index(path) is not None
