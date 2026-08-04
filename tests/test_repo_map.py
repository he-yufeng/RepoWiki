"""repo map command: ranked output without LLM calls."""

import json

from click.testing import CliRunner

from repowiki.cli import cli


def _make_repo(tmp_path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "engine.py").write_text(
        "from .store import save\nfrom .cache import warm\n\ndef run(): ...\n"
    )
    (tmp_path / "core" / "store.py").write_text("from .cache import warm\n\ndef save(): ...\n")
    (tmp_path / "core" / "cache.py").write_text("def warm(): ...\n")
    (tmp_path / "notes.py").write_text("# orphan file\n")


def test_map_json_ranks_by_dependency_pagerank(tmp_path):
    _make_repo(tmp_path)
    result = CliRunner().invoke(cli, ["map", str(tmp_path), "--format", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["file_count"] == 4
    paths = [entry["path"] for entry in payload["entries"]]
    # cache.py sits at the bottom of every import chain, so it outranks the rest
    assert paths[0] == "core/cache.py"
    assert payload["entries"][0]["score"] >= payload["entries"][-1]["score"]
    assert payload["entries"][0]["rank"] == 1


def test_map_text_lists_files_and_top_limit(tmp_path):
    _make_repo(tmp_path)
    result = CliRunner().invoke(cli, ["map", str(tmp_path), "--top", "2"])

    assert result.exit_code == 0, result.output
    assert "core/cache.py" in result.output
    assert "engine.py" not in result.output  # trimmed by --top 2


def test_map_rejects_urls():
    result = CliRunner().invoke(cli, ["map", "https://github.com/octocat/hello"])
    assert result.exit_code != 0
    assert "local directories only" in result.output
