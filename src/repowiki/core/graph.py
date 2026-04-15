"""dependency graph construction and PageRank ranking."""

from __future__ import annotations

import re
from pathlib import Path

import networkx as nx

from repowiki.core.models import ProjectContext

# import pattern regexes by language
_IMPORT_PATTERNS = {
    "python": [
        re.compile(r"^\s*import\s+([\w.]+)", re.MULTILINE),
        re.compile(r"^\s*from\s+([\w.]+)\s+import", re.MULTILINE),
    ],
    "javascript": [
        re.compile(r"""import\s+.*?\s+from\s+['"]([^'"]+)['"]""", re.MULTILINE),
        re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""", re.MULTILINE),
    ],
    "typescript": [
        re.compile(r"""import\s+.*?\s+from\s+['"]([^'"]+)['"]""", re.MULTILINE),
        re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""", re.MULTILINE),
    ],
    "go": [
        re.compile(r'"([^"]+)"', re.MULTILINE),
    ],
    "rust": [
        re.compile(r"^\s*use\s+([\w:]+)", re.MULTILINE),
        re.compile(r"^\s*mod\s+(\w+)", re.MULTILINE),
    ],
    "java": [
        re.compile(r"^\s*import\s+([\w.]+);", re.MULTILINE),
    ],
}

# also cover jsx/tsx/mjs etc
for alias in ("jsx", "tsx", "mjs", "cjs"):
    _IMPORT_PATTERNS[alias] = _IMPORT_PATTERNS["javascript"]


class DependencyGraph:
    """file dependency graph with PageRank scoring."""

    def __init__(self):
        self.graph = nx.DiGraph()
        self._file_paths: set[str] = set()

    @classmethod
    def build_from_project(cls, project: ProjectContext) -> DependencyGraph:
        dg = cls()
        path_set = {f.path for f in project.files}
        dg._file_paths = path_set

        # add all files as nodes
        for f in project.files:
            dg.graph.add_node(f.path, language=f.language, lines=f.lines)

        # parse imports and create edges
        for f in project.files:
            content = f.content or f.preview
            if not content:
                continue

            patterns = _IMPORT_PATTERNS.get(f.language, [])
            for pat in patterns:
                for match in pat.finditer(content):
                    import_path = match.group(1)
                    resolved = _resolve_import(import_path, f.path, f.language, path_set)
                    if resolved and resolved != f.path:
                        dg.graph.add_edge(f.path, resolved)

        return dg

    def rank_files(self) -> list[tuple[str, float]]:
        """return files ranked by PageRank (most important first)."""
        if not self.graph.nodes:
            return []
        try:
            scores = nx.pagerank(self.graph, alpha=0.85)
        except nx.PowerIterationFailedConvergence:
            scores = {n: 1.0 / len(self.graph) for n in self.graph}
        return sorted(scores.items(), key=lambda x: -x[1])

    def get_core_files(self, top_n: int = 10) -> list[str]:
        """top N most important files by PageRank."""
        return [path for path, _ in self.rank_files()[:top_n]]

    def get_module_dependencies(self) -> dict[str, set[str]]:
        """edges between top-level directory modules."""
        deps: dict[str, set[str]] = {}
        for src, dst in self.graph.edges:
            src_mod = _get_module(src)
            dst_mod = _get_module(dst)
            if src_mod != dst_mod:
                deps.setdefault(src_mod, set()).add(dst_mod)
        return deps

    def to_mermaid(self) -> str:
        """generate a Mermaid flowchart of inter-module dependencies."""
        mod_deps = self.get_module_dependencies()
        if not mod_deps:
            return ""

        lines = ["graph TD"]
        seen_edges = set()
        for src, targets in sorted(mod_deps.items()):
            for dst in sorted(targets):
                edge = (src, dst)
                if edge not in seen_edges:
                    seen_edges.add(edge)
                    # sanitize node names for Mermaid
                    s = _mermaid_id(src)
                    d = _mermaid_id(dst)
                    lines.append(f"  {s}[{src}] --> {d}[{dst}]")

        return "\n".join(lines)

    def get_entry_points(self) -> list[str]:
        """files with zero or very few incoming edges (likely entry points)."""
        entries = []
        for node in self.graph.nodes:
            if self.graph.in_degree(node) <= 1:
                entries.append(node)
        return entries


def _get_module(path: str) -> str:
    parts = Path(path).parts
    if len(parts) <= 1:
        return "root"
    mod = parts[0]
    if mod in ("src", "lib", "pkg", "internal", "app") and len(parts) > 2:
        return parts[1]
    return mod


def _mermaid_id(name: str) -> str:
    """make a valid Mermaid node ID from a module name."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", name)


def _resolve_import(
    import_path: str,
    source_file: str,
    language: str,
    known_paths: set[str],
) -> str | None:
    """try to resolve an import string to an actual file path in the project."""
    if language in ("python", "pyi"):
        # convert dots to slashes: "foo.bar.baz" -> "foo/bar/baz"
        rel = import_path.replace(".", "/")
        candidates = [
            f"{rel}.py",
            f"{rel}/__init__.py",
            f"src/{rel}.py",
            f"src/{rel}/__init__.py",
        ]
    elif language in ("javascript", "typescript", "jsx", "tsx", "mjs", "cjs"):
        if import_path.startswith("."):
            # relative import
            base_dir = str(Path(source_file).parent)
            rel = str(Path(base_dir) / import_path)
        else:
            rel = import_path
        candidates = [
            rel,
            f"{rel}.ts", f"{rel}.tsx", f"{rel}.js", f"{rel}.jsx",
            f"{rel}/index.ts", f"{rel}/index.tsx", f"{rel}/index.js",
        ]
    elif language == "go":
        # go imports are package paths, hard to resolve without go.mod
        parts = import_path.split("/")
        if len(parts) >= 2:
            candidates = [f"{'/'.join(parts[-2:])}.go"]
        else:
            return None
    elif language == "rust":
        rel = import_path.split("::")[0].replace("::", "/")
        candidates = [f"src/{rel}.rs", f"src/{rel}/mod.rs", f"{rel}.rs"]
    elif language == "java":
        rel = import_path.replace(".", "/")
        candidates = [f"src/main/java/{rel}.java", f"{rel}.java"]
    else:
        return None

    for c in candidates:
        # normalize path
        c = str(Path(c))
        if c in known_paths:
            return c

    return None
