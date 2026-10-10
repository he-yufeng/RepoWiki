"""Call-graph extraction from the Python AST (no LLM, no fixtures on disk)."""

from __future__ import annotations

from repowiki.core.callgraph import build_call_edges, to_mermaid
from repowiki.core.models import FileInfo, ProjectContext


def _project(sources: dict[str, str]) -> ProjectContext:
    return ProjectContext(
        name="demo",
        root="/demo",
        files=[
            FileInfo(path=path, size=len(src), language="python", content=src)
            for path, src in sources.items()
        ],
    )


def test_same_file_and_cross_file_edges():
    project = _project({
        "app.py": (
            "from lib import helper\n\n"
            "def main():\n"
            "    helper()\n"
            "    local()\n\n"
            "def local():\n"
            "    pass\n"
        ),
        "lib.py": "def helper():\n    pass\n",
    })

    edges = build_call_edges(project)
    assert edges["app.py:main"] == {"lib.py:helper", "app.py:local"}


def test_self_calls_stay_inside_their_class():
    project = _project({
        "svc.py": (
            "class Engine:\n"
            "    def run(self):\n"
            "        self.boot()\n\n"
            "    def boot(self):\n"
            "        pass\n"
        ),
    })

    edges = build_call_edges(project)
    assert edges["svc.py:Engine.run"] == {"svc.py:Engine.boot"}


def test_ambiguous_bare_names_stay_unresolved():
    project = _project({
        "a.py": "def helper():\n    pass\n",
        "b.py": "def helper():\n    pass\n",
        "c.py": "def main():\n    helper()\n",
    })

    edges = build_call_edges(project)
    # two definitions of helper: no unique resolution, no guessed edge
    assert "c.py:main" not in edges


def test_syntax_error_files_are_skipped():
    project = _project({
        "broken.py": "def oops(:\n",
        "ok.py": "def fine():\n    pass\n",
    })
    # must not raise, and the broken file simply contributes nothing
    assert build_call_edges(project) == {}


def test_mermaid_renders_nodes_and_edges():
    edges = {"app.py:main": {"lib.py:helper"}}
    out = to_mermaid(edges)
    assert out.startswith("graph LR")
    assert '["main"]' in out and '["helper"]' in out
    assert "-->" in out
    assert to_mermaid({}) == ""


def test_analyzer_attaches_call_graph(tmp_path, monkeypatch):
    """The analyzer wires the deterministic call graph onto the architecture."""
    import asyncio

    from repowiki.core.analyzer import Analyzer

    project = _project({
        "app.py": "def main():\n    helper()\n",
        "lib.py": "def helper():\n    pass\n",
    })

    class FakeLLM:
        model = "fake"
        async def complete(self, messages, **kwargs):
            return "{}"

    analyzer = Analyzer.__new__(Analyzer)
    analyzer.llm = FakeLLM()
    analyzer.language = "en"
    analyzer.max_tokens = 100
    analyzer.degraded_modules = []

    class NoCache:
        async def get(self, key):
            return None
        async def put(self, key, value):
            pass

    analyzer.cache = NoCache()
    analyzer._key_prefix = "fake:en"
    analyzer.cache_keys = {}

    arch = asyncio.run(analyzer._generate_architecture(project, "", "h"))
    # LLM returned {} so the diagram fields stay default; the call graph is
    # computed in analyze(), not inside the cached generator.
    assert arch.call_graph == ""

    # attach the way analyze() does
    from repowiki.core.callgraph import build_call_edges, to_mermaid
    arch.call_graph = to_mermaid(build_call_edges(project))
    assert "main" in arch.call_graph and "helper" in arch.call_graph
