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
