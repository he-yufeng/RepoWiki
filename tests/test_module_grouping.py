"""Module grouping: small modules stay flat, oversize modules subdivide."""
from __future__ import annotations

from repowiki.core.analyzer import Analyzer
from repowiki.core.models import FileInfo


def _f(path: str) -> FileInfo:
    return FileInfo(path=path, size=10, language="python", lines=1, preview="x", content="x")


def _grouped(paths: list[str], threshold: int = 10) -> dict[str, list[FileInfo]]:
    analyzer = Analyzer(llm=None, cache=None)
    return analyzer._group_into_modules([_f(p) for p in paths], split_threshold=threshold)


def test_small_module_stays_flat():
    groups = _grouped([
        "src/repowiki/cli.py",
        "src/repowiki/config.py",
        "src/repowiki/__init__.py",
    ])
    assert "repowiki" in groups
    assert len(groups["repowiki"]) == 3


def test_oversize_module_splits_by_subdir():
    paths = (
        [f"src/repowiki/core/file{i}.py" for i in range(8)]
        + [f"src/repowiki/llm/file{i}.py" for i in range(4)]
        + ["src/repowiki/__init__.py"]
    )
    groups = _grouped(paths, threshold=5)

    # 13 files in the "repowiki" bucket > threshold 5 -> must split
    assert "repowiki" not in groups
    assert "repowiki/core" in groups
    assert "repowiki/llm" in groups
    assert len(groups["repowiki/core"]) == 8
    assert len(groups["repowiki/llm"]) == 4


def test_split_degenerates_to_single_bucket_keeps_original():
    """if all files happen to share the next segment, splitting is pointless;
    keep the original name."""
    paths = [f"src/repowiki/core/file{i}.py" for i in range(20)]
    groups = _grouped(paths, threshold=5)
    # top-level grouping puts everything under "repowiki" (src/ is a wrapper).
    # _split_module then sees only the "core" sub-segment -> degenerate bucket,
    # so we keep "repowiki" rather than producing repowiki/core alone.
    assert "repowiki" in groups
    assert len(groups["repowiki"]) == 20


def test_root_files_grouped_separately():
    groups = _grouped(["README.md", "pyproject.toml", "src/repowiki/cli.py"])
    assert "root" in groups
    assert len(groups["root"]) == 2
    assert "repowiki" in groups
