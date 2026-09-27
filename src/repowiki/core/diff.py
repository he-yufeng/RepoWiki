"""review-order analysis for a git diff: rank changed files by real importance."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field

import networkx as nx

from repowiki.core.graph import DependencyGraph


@dataclass
class ChangedFile:
    """one file touched by the diff, in review order."""

    path: str
    change: str  # M / A / D / R
    old_path: str = ""  # rename source, when change == R
    rank: int = 0  # position in the repo-wide PageRank order; 0 = unranked
    score: float = 0.0
    direct_dependents: int = 0  # files that import it
    transitive_dependents: int = 0  # files that transitively import it


@dataclass
class DiffReport:
    """the full review guide for one refspec."""

    root: str
    refspec: str
    files: list[ChangedFile] = field(default_factory=list)

    @property
    def deleted(self) -> list[ChangedFile]:
        return [f for f in self.files if f.change == "D"]


def diff_files(root: str, refspec: str) -> list[tuple[str, str, str]]:
    """changed (status, path, old_path) triples for a refspec.

    Accepts A...B, A..B, or a single ref (diffed against the worktree);
    `git diff --name-status` treats them the same at this layer.
    """
    out = subprocess.run(
        ["git", "-C", root, "diff", "--name-status", "-z", refspec],
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8", errors="replace")
    # -z format: STATUS\0PATH\0, renames: R100\0OLD\0NEW\0
    parts = [p for p in out.split("\0") if p != ""]
    result: list[tuple[str, str, str]] = []
    i = 0
    while i < len(parts):
        status = parts[i]
        if status.startswith("R") or status.startswith("C"):
            old_path, new_path = parts[i + 1], parts[i + 2]
            result.append(("R", new_path, old_path))
            i += 3
        else:
            result.append((status[:1], parts[i + 1], ""))
            i += 2
    return result


def build_diff_report(root: str, refspec: str, graph: DependencyGraph) -> DiffReport:
    """rank the diff's files into review order.

    Changed files are ranked by the graph of the current worktree: a file's
    PageRank plus how many files (transitively) import it. Deleted files are
    listed last — they are gone from the graph but still deserve a look.
    """
    changes = diff_files(root, refspec)
    ranked = graph.rank_files()
    rank_of = {path: i + 1 for i, (path, _) in enumerate(ranked)}
    score_of = dict(ranked)

    files: list[ChangedFile] = []
    for status, path, old_path in changes:
        entry = ChangedFile(path=path, change=status, old_path=old_path)
        if status != "D" and path in graph.graph:
            entry.rank = rank_of.get(path, 0)
            entry.score = score_of.get(path, 0.0)
            entry.direct_dependents = len(list(graph.graph.predecessors(path)))
            # ancestors = everything that imports this file, directly or not
            entry.transitive_dependents = len(nx.ancestors(graph.graph, path))
        files.append(entry)

    files.sort(key=lambda f: (f.change == "D", -f.score, f.rank, f.path))
    return DiffReport(root=root, refspec=refspec, files=files)
