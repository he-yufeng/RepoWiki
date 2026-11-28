"""Exercise the trace command on a small graph built from real imports."""

import json
import os

from click.testing import CliRunner

from repowiki.cli import cli


def _repo(tmp_path):
    root = tmp_path / "http-local"
    src = root / "src"
    src.mkdir(parents=True)
    files = {
        "entry.py": "from .z import value\nfrom .a import value\n",
        "a.py": "from .entry import value\nfrom .leaf import value\n",
        "z.py": "from .leaf import value\n",
        "leaf.py": "value = 1\n",
        "isolated.py": "value = 2\n",
    }
    for name, text in files.items():
        (src / name).write_text(text, encoding="utf-8")
    return root


def _trace(root, source, target, fmt="json"):
    return CliRunner().invoke(cli, ["trace", str(root), source, target, "--format", fmt])


def test_trace_chooses_one_shortest_directed_chain_through_a_cycle(tmp_path):
    root = _repo(tmp_path)
    source = f"src{os.sep}entry.py"
    result = _trace(root, source, "src/leaf.py")

    assert result.exit_code == 0, result.output
    assert not result.stderr
    assert json.loads(result.stdout) == {
        "source": "src/entry.py",
        "target": "src/leaf.py",
        "path": ["src/entry.py", "src/a.py", "src/leaf.py"],
        "hops": 2,
    }

    text = _trace(root, "src/entry.py", "src/leaf.py", "text")
    assert text.exit_code == 0, text.output
    assert "src/entry.py -> src/a.py -> src/leaf.py" in text.stdout


def test_trace_unreachable_and_known_self_have_different_results(tmp_path):
    root = _repo(tmp_path)
    reverse = _trace(root, "src/leaf.py", "src/entry.py")
    same = _trace(root, "src/isolated.py", "src/isolated.py")

    assert reverse.exit_code == same.exit_code == 0, reverse.output + same.output
    assert json.loads(reverse.stdout) == {
        "source": "src/leaf.py", "target": "src/entry.py", "path": None, "hops": None,
    }
    assert json.loads(same.stdout) == {
        "source": "src/isolated.py", "target": "src/isolated.py", "path": ["src/isolated.py"], "hops": 0,
    }


def test_trace_reports_unindexed_paths_not_unreachable_paths(tmp_path):
    root = _repo(tmp_path)
    (root / ".gitignore").write_text("src/ignored.py\n", encoding="utf-8")
    (root / "src/ignored.py").write_text("value = 3\n", encoding="utf-8")

    result = _trace(root, "src/ignored.py", "src/ignored.py")
    assert result.exit_code == 2
    assert "not indexed" in result.stderr.lower()
    assert not result.stdout


def test_trace_keeps_partial_coverage_warning_out_of_json(tmp_path):
    root = _repo(tmp_path)
    (root / "src/binary.py").write_bytes(b"\x00\x7f\x01" * 16)
    result = _trace(root, "src/entry.py", "src/leaf.py")

    assert result.exit_code == 0, result.output
    assert "Partial coverage:" in result.stderr
    payload = json.loads(result.stdout)
    assert payload["path"] == ["src/entry.py", "src/a.py", "src/leaf.py"]
    assert "binary" in payload["partial_coverage"]


def test_trace_accepts_local_directory_named_like_http(tmp_path):
    root = _repo(tmp_path)
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        relative = os.path.relpath(root)
        result = runner.invoke(cli, ["trace", relative, "src/a.py", "src/leaf.py", "--format", "json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["hops"] == 1
