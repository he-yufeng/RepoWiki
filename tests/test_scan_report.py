"""Scan coverage reporting: a partial scan must say so, loudly.

Reading an incomplete wiki that claims to be complete is worse than an
incomplete one. These tests pin the report fields and the overview-page
coverage note.
"""

from repowiki.core.models import ProjectContext, ProjectOverview, ScanReport
from repowiki.core.scanner import scan_directory
from repowiki.core.wiki_builder import WikiBuilder
from repowiki.ingest.local import ingest_local


def test_report_counts_oversized_files_with_example_paths(tmp_path):
    big = tmp_path / "huge.py"
    big.write_text("x = 1\n" * 45000, encoding="utf-8")
    (tmp_path / "small.py").write_text("y = 2\n", encoding="utf-8")

    report = ScanReport()
    files = scan_directory(tmp_path, max_file_size=200 * 1024, report=report)

    assert {f.path for f in files} == {"small.py"}
    assert report.candidates == 2
    assert report.kept == 1
    assert report.oversized_count == 1
    assert report.oversized == ["huge.py"]
    assert report.partial


def test_report_marks_full_coverage_as_not_partial(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("y = 2\n", encoding="utf-8")

    report = ScanReport()
    scan_directory(tmp_path, report=report)

    assert report.candidates == report.kept == 2
    assert not report.partial


def test_report_counts_priority_cap_drops(tmp_path):
    for i in range(10):
        (tmp_path / f"mod{i}.py").write_text(f"x = {i}\n", encoding="utf-8")

    report = ScanReport()
    files = scan_directory(tmp_path, max_files=3, report=report)

    assert len(files) == 3
    assert report.candidates == 10
    assert report.kept == 3
    assert report.priority_dropped == 7
    assert report.partial


def test_report_lists_skipped_directories(tmp_path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lib.js").write_text("x\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x = 1\n", encoding="utf-8")

    report = ScanReport()
    scan_directory(tmp_path, report=report)

    assert "node_modules" in report.skipped_dirs
    assert report.kept == 1


def test_ingest_local_attaches_the_coverage_report(tmp_path):
    big = tmp_path / "huge.py"
    big.write_text("x = 1\n" * 45000, encoding="utf-8")
    (tmp_path / "small.py").write_text("y = 2\n", encoding="utf-8")

    ctx = ingest_local(tmp_path, max_file_size=200 * 1024)

    assert ctx.coverage is not None
    assert ctx.coverage.partial
    assert ctx.coverage.oversized_count == 1


def _ctx_with_coverage(tmp_path, report):
    return ProjectContext(
        name="demo",
        root=str(tmp_path),
        files=[],
        file_tree="",
        coverage=report,
    )


def _overview():
    return ProjectOverview(name="demo", one_liner="a demo")


def test_overview_page_flags_partial_coverage(tmp_path):
    report = ScanReport(candidates=10, kept=3, oversized=["huge.py"], oversized_count=1, priority_dropped=6)
    md = WikiBuilder()._build_overview_page(_overview(), _ctx_with_coverage(tmp_path, report))

    assert "Partial coverage" in md
    assert "3 of 10 files" in md
    assert "huge.py" in md


def test_overview_page_stays_quiet_on_full_coverage(tmp_path):
    report = ScanReport(candidates=3, kept=3)
    md = WikiBuilder()._build_overview_page(_overview(), _ctx_with_coverage(tmp_path, report))

    assert "Partial coverage" not in md
