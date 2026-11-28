"""Exercise the impact command on a real import graph."""

import json
import os

from click.testing import CliRunner

from repowiki.cli import cli


def _repo(tmp_path):
    root = tmp_path / "mini"
    src = root / "src"
    src.mkdir(parents=True)
    files = {
        "entry.py": "from .a import value\n",
        "a.py": "from .leaf import value\n",
        "z.py": "from .leaf import value\n",
        "leaf.py": "value = 1\n",
        "isolated.py": "value = 2\n",
    }
    for name, text in files.items():
        (src / name).write_text(text, encoding="utf-8")
    return root


def _impact(root, file, *args):
    return CliRunner().invoke(cli, ["impact", str(root), file, *args])


def test_impact_lists_transitive_importers_nearest_first(tmp_path):
    root = _repo(tmp_path)
    result = _impact(root, f"src{os.sep}leaf.py", "--format", "json")

    assert result.exit_code == 0, result.output
    assert not result.stderr
    assert json.loads(result.stdout) == {
        "file": "src/leaf.py",
        "dependents": [
            {"path": "src/a.py", "distance": 1},
            {"path": "src/z.py", "distance": 1},
            {"path": "src/entry.py", "distance": 2},
        ],
        "direct": 2,
        "total": 3,
    }

    text = _impact(root, "src/leaf.py")
    assert text.exit_code == 0, text.output
    assert "3 files import src/leaf.py" in text.stdout
    assert text.stdout.index("src/a.py") < text.stdout.index("src/entry.py")


def test_impact_depth_limit_keeps_direct_importers(tmp_path):
    root = _repo(tmp_path)
    result = _impact(root, "src/leaf.py", "--depth", "1", "--format", "json")

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["dependents"] == [
        {"path": "src/a.py", "distance": 1},
        {"path": "src/z.py", "distance": 1},
    ]


def test_impact_isolated_file_reports_nothing(tmp_path):
    root = _repo(tmp_path)
    result = _impact(root, "src/isolated.py", "--format", "json")

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {
        "file": "src/isolated.py", "dependents": [], "direct": 0, "total": 0,
    }

    text = _impact(root, "src/isolated.py")
    assert text.exit_code == 0, text.output
    assert "No file in the scanned graph imports src/isolated.py." in text.stdout


def test_impact_unknown_endpoint_is_a_usage_error(tmp_path):
    root = _repo(tmp_path)
    result = _impact(root, "src/missing.py")

    assert result.exit_code == 2
    assert "not indexed" in result.output


def test_impact_rejects_zero_depth(tmp_path):
    result = _impact(_repo(tmp_path), "src/leaf.py", "--depth", "0")

    assert result.exit_code == 2
    assert "Invalid value for '--depth'" in result.stderr and not result.stdout


def test_impact_preserves_partial_scan_warning_outside_json(tmp_path):
    root = _repo(tmp_path)
    (root / "src/binary.py").write_bytes(b"\x00\x7f\x01" * 16)
    result = _impact(root, "src/leaf.py", "--format", "json")

    assert result.exit_code == 0, result.output
    assert "Partial coverage:" in result.stderr
    payload = json.loads(result.stdout)
    assert payload["total"] == 3 and "binary" in payload["partial_coverage"]


def test_impact_ignores_the_file_itself_in_a_cycle(tmp_path):
    root = tmp_path / "cycle"
    src = root / "src"
    src.mkdir(parents=True)
    (src / "one.py").write_text("from .two import value\n", encoding="utf-8")
    (src / "two.py").write_text("from .one import value\n", encoding="utf-8")

    result = _impact(root, "src/one.py", "--format", "json")

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {
        "file": "src/one.py",
        "dependents": [{"path": "src/two.py", "distance": 1}],
        "direct": 1,
        "total": 1,
    }
