"""Smoke tests — import every public module so CI at least fails on
ImportError regressions. Real unit tests can grow inside this directory."""
import importlib


def test_package_imports():
    m = importlib.import_module("repowiki")
    assert m is not None


def test_cli_entrypoint_imports():
    importlib.import_module("repowiki.cli")


def test_version_string():
    m = importlib.import_module("repowiki")
    v = getattr(m, "__version__", None)
    assert v is None or isinstance(v, str)


def check_installed_trace(wheel):
    import hashlib
    import json
    import os
    import subprocess
    import sysconfig
    from importlib.metadata import version
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from zipfile import ZipFile

    import repowiki

    package = Path(repowiki.__file__).resolve().parent
    assert package.is_relative_to(Path(sysconfig.get_path("purelib")).resolve())
    assert repowiki.__version__ == version("repowiki")
    assert (package / "server/static/index.html").is_file()
    with ZipFile(wheel) as archive:
        for source in ("cli.py", "core/graph.py"):
            assert (package / source).read_bytes() == archive.read(f"repowiki/{source}")
    cli = Path(sysconfig.get_path("scripts")) / ("repowiki.exe" if os.name == "nt" else "repowiki")
    with TemporaryDirectory(prefix="repowiki-wheel-trace-") as work:
        repo = Path(work) / "fixture"
        repo.mkdir()
        for name, text in {"entry.py": "import middle\n", "middle.py": "import leaf\n", "leaf.py": "value = 1\n"}.items():
            (repo / name).write_text(text, encoding="utf-8")
        env = {**os.environ, "HOME": work, "USERPROFILE": work}
        env.pop("PYTHONPATH", None)
        result = subprocess.run(
            [str(cli), "trace", str(repo), "entry.py", "leaf.py", "--format", "json"],
            cwd=work, env=env, capture_output=True, text=True, encoding="utf-8", check=True, timeout=20,
        )
        assert not result.stderr, result.stderr
        assert json.loads(result.stdout) == {
            "source": "entry.py", "target": "leaf.py", "path": ["entry.py", "middle.py", "leaf.py"], "hops": 2,
        }
    print(json.dumps({"traceExit": result.returncode, "version": repowiki.__version__,
                      "wheelSha256": hashlib.sha256(wheel.read_bytes()).hexdigest(), "packageRoot": str(package)}))


if __name__ == "__main__":
    import sys
    from pathlib import Path

    check_installed_trace(Path(sys.argv[1]))
