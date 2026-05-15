"""Cache key granularity: arch / guide should not invalidate on body edits."""
from __future__ import annotations

from repowiki.core.analyzer import Analyzer
from repowiki.core.models import FileInfo, ProjectContext


def _project(files: list[FileInfo]) -> ProjectContext:
    return ProjectContext(
        name="x", root="/tmp/x", files=files,
        file_tree="\n".join(f.path for f in files),
    )


def _file(path: str, content: str, size: int | None = None) -> FileInfo:
    body = content
    return FileInfo(
        path=path,
        size=size if size is not None else len(body.encode()),
        language="python",
        lines=body.count("\n") + 1,
        preview=body,
        content=body,
    )


def test_structure_hash_ignores_source_body_changes():
    """editing the body of a regular source file with the same size
    must not change the structure hash that arch / guide cache uses."""
    p1 = _project([_file("src/foo.py", "def a(): return 1\n", size=200)])
    p2 = _project([_file("src/foo.py", "def b(): return 2\n", size=200)])

    assert Analyzer._structure_hash(p1) == Analyzer._structure_hash(p2)


def test_structure_hash_changes_when_file_added():
    p1 = _project([_file("src/foo.py", "x", size=10)])
    p2 = _project([
        _file("src/foo.py", "x", size=10),
        _file("src/bar.py", "y", size=10),
    ])

    assert Analyzer._structure_hash(p1) != Analyzer._structure_hash(p2)


def test_structure_hash_changes_when_size_changes():
    p1 = _project([_file("src/foo.py", "x", size=10)])
    p2 = _project([_file("src/foo.py", "x", size=20)])

    assert Analyzer._structure_hash(p1) != Analyzer._structure_hash(p2)


def test_overview_hash_changes_with_readme_edit():
    """README content does affect overview, even with same structure."""
    structure = Analyzer._structure_hash(_project([_file("README.md", "v1", size=10)]))

    p1 = _project([_file("README.md", "Project Foo\n\nDoes things.", size=10)])
    p2 = _project([_file("README.md", "Project Bar\n\nDoes other things.", size=10)])

    h1 = Analyzer._overview_hash(p1, structure)
    h2 = Analyzer._overview_hash(p2, structure)
    assert h1 != h2


def test_overview_hash_stable_for_unrelated_source_edit():
    """editing src/foo.py should NOT bust overview cache (README untouched, same size)."""
    structure_p1 = Analyzer._structure_hash(_project([
        _file("README.md", "Same readme", size=20),
        _file("src/foo.py", "v1 body", size=100),
    ]))
    structure_p2 = Analyzer._structure_hash(_project([
        _file("README.md", "Same readme", size=20),
        _file("src/foo.py", "v2 body", size=100),
    ]))

    p1 = _project([
        _file("README.md", "Same readme", size=20),
        _file("src/foo.py", "v1 body", size=100),
    ])
    p2 = _project([
        _file("README.md", "Same readme", size=20),
        _file("src/foo.py", "v2 body", size=100),
    ])

    assert structure_p1 == structure_p2
    assert Analyzer._overview_hash(p1, structure_p1) == Analyzer._overview_hash(p2, structure_p2)
