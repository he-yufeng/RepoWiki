"""Deterministic Python call graph, built from the AST — no LLM involved.

Scope is deliberately narrow: same-file calls, `self.` methods within their
class, and cross-file calls through explicit `from x import f` imports.
Everything else (attributes, dynamic dispatch, dunder plumbing) is skipped
rather than guessed. The graph is for orientation, not proof.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

from .models import ProjectContext

# Orientation aid, not a build artifact: cap the picture so a huge project
# still renders something readable instead of a hairball.
MAX_NODES = 120
MAX_EDGES = 300


@dataclass
class _Def:
    node: ast.FunctionDef | ast.AsyncFunctionDef
    file: str
    qualname: str  # "Class.method" or "func" (nested funcs get dotted too)

    @property
    def node_id(self) -> str:
        return f"{self.file}:{self.qualname}"


def _collect_defs(tree: ast.Module, path: str) -> list[_Def]:
    defs: list[_Def] = []

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = f"{prefix}{child.name}"
                defs.append(_Def(node=child, file=path, qualname=qual))
                walk(child, f"{qual}.")
            elif isinstance(child, ast.ClassDef):
                walk(child, f"{prefix}{child.name}.")
            else:
                walk(child, prefix)

    walk(tree, "")
    return defs


def _explicit_imports(tree: ast.Module, path: str, path_set: set[str]) -> dict[str, str]:
    """Map names brought in by `from m import f` to the defining file, when the
    module resolves inside the project."""
    from .graph import _resolve_import

    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            target = _resolve_import(node.module, path, "python", path_set)
            if target:
                for alias in node.names:
                    out[alias.asname or alias.name] = target
    return out


def build_call_edges(project: ProjectContext) -> dict[str, set[str]]:
    """Return caller node id -> set of callee node ids for Python files."""
    py_files = [f for f in project.files if f.language == "python" and (f.content or f.preview)]
    path_set = {f.path for f in project.files}

    defs_by_file: dict[str, list[_Def]] = {}
    by_id: dict[str, _Def] = {}
    bare: dict[str, list[_Def]] = {}
    trees: dict[str, ast.Module] = {}
    for f in py_files:
        try:
            tree = ast.parse(f.content or f.preview or "")
        except SyntaxError:
            continue
        trees[f.path] = tree
        defs = _collect_defs(tree, f.path)
        defs_by_file[f.path] = defs
        for d in defs:
            by_id[d.node_id] = d
            bare.setdefault(d.qualname.split(".")[-1], []).append(d)

    def resolve(name: str, file: str, class_prefix: str, imports: dict[str, str]) -> str | None:
        # self.x() inside a class resolves only within that class
        if class_prefix:
            candidate = f"{file}:{class_prefix}{name}"
            if candidate in by_id:
                return candidate
        # same file: exact qualname first, then a unique endswith match
        same_file = defs_by_file.get(file, [])
        for d in same_file:
            if d.qualname == name:
                return d.node_id
        tail = [d for d in same_file if "." not in name and d.qualname.endswith(f".{name}")]
        if len(tail) == 1:
            return tail[0].node_id
        # an explicit `from x import name` pulls in that file's def
        target = imports.get(name)
        if target:
            for d in defs_by_file.get(target, []):
                if d.qualname.split(".")[-1] == name:
                    return d.node_id
        # last resort: exactly one project-wide definition of the bare name
        candidates = bare.get(name, [])
        if len(candidates) == 1:
            return candidates[0].node_id
        return None

    edges: dict[str, set[str]] = {}
    for f in py_files:
        tree = trees.get(f.path)
        if tree is None:
            continue
        imports = _explicit_imports(tree, f.path, path_set)
        for d in defs_by_file.get(f.path, []):
            class_prefix = ""
            if "." in d.qualname:
                class_prefix = d.qualname.rsplit(".", 1)[0] + "."
            for node in ast.walk(d.node):
                name: str | None = None
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        name = node.func.id
                    elif (
                        isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "self"
                    ):
                        name = node.func.attr
                if name is None:
                    continue
                target = resolve(name, f.path, class_prefix, imports)
                if target and target != d.node_id:
                    edges.setdefault(d.node_id, set()).add(target)

    # cap by degree so the render stays a map, not a hairball
    degree: dict[str, int] = {}
    for src, dsts in edges.items():
        degree[src] = degree.get(src, 0) + len(dsts)
        for dst in dsts:
            degree[dst] = degree.get(dst, 0) + 1
    keep = {n for n, _ in sorted(degree.items(), key=lambda kv: -kv[1])[:MAX_NODES]}
    pruned: dict[str, set[str]] = {}
    budget = MAX_EDGES
    for src in sorted(edges, key=lambda s: -degree.get(s, 0)):
        if src not in keep:
            continue
        dsts = [d for d in sorted(edges[src]) if d in keep]
        pruned[src] = set(dsts[: max(budget, 0)])
        budget -= len(pruned[src])
        if budget <= 0:
            break
    return {s: ds for s, ds in pruned.items() if ds}


def _mermaid_id(node_id: str) -> str:
    return "n_" + "".join(ch if ch.isalnum() else "_" for ch in node_id)


def to_mermaid(edges: dict[str, set[str]]) -> str:
    """Render the call graph as a Mermaid left-to-right flowchart."""
    if not edges:
        return ""
    lines = ["graph LR"]
    seen: set[str] = set()
    for src in sorted(edges):
        for dst in sorted(edges[src]):
            for nid in (src, dst):
                if nid not in seen:
                    seen.add(nid)
                    short = nid.split(":", 1)[1] if ":" in nid else nid
                    lines.append(f'    {_mermaid_id(nid)}["{short}"]')
            lines.append(f"    {_mermaid_id(src)} --> {_mermaid_id(dst)}")
    return "\n".join(lines) + "\n"
