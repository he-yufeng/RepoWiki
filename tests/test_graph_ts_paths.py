"""TypeScript path-alias resolution in the dependency graph."""
from __future__ import annotations

from repowiki.core.graph import (
    DependencyGraph,
    _apply_ts_alias,
    _load_ts_aliases,
    _resolve_import,
    _strip_jsonc,
)
from repowiki.core.models import FileInfo, ProjectContext


def _f(path: str, content: str = "", language: str = "typescript") -> FileInfo:
    return FileInfo(
        path=path, size=len(content.encode()), language=language,
        lines=content.count("\n") + 1, preview=content, content=content,
    )


def test_strip_jsonc_handles_comments_and_trailing_commas():
    raw = """{
        // a line comment
        "compilerOptions": {
            /* block
               comment */
            "baseUrl": ".",
            "paths": { "@/*": ["src/*"], }, // trailing comma
        },
    }"""
    import json
    parsed = json.loads(_strip_jsonc(raw))
    assert parsed["compilerOptions"]["paths"]["@/*"] == ["src/*"]


def test_load_ts_aliases_basic():
    tsconfig = _f("tsconfig.json", '{"compilerOptions":{"baseUrl":".","paths":{"@/*":["src/*"]}}}', "json")
    aliases = _load_ts_aliases([tsconfig])
    assert aliases == {"@/*": ["src/*"]}


def test_load_ts_aliases_with_baseurl_subdir():
    """baseUrl=./src means @/foo -> frontend/src/foo (anchor walks
    config_dir + baseUrl). Trailing /* is preserved so _apply_ts_alias
    can substitute it."""
    tsconfig = _f("frontend/tsconfig.json",
                  '{"compilerOptions":{"baseUrl":"./src","paths":{"@/*":["./*"]}}}', "json")
    aliases = _load_ts_aliases([tsconfig])
    assert aliases == {"@/*": ["frontend/src/*"]}


def test_apply_alias_substitutes_wildcard():
    aliases = {"@/*": ["src/*"]}
    assert _apply_ts_alias("@/lib/foo", aliases) == ["src/lib/foo"]


def test_resolve_ts_alias_finds_file():
    known = {"src/lib/foo.ts"}
    aliases = {"@/*": ["src/*"]}
    resolved = _resolve_import("@/lib/foo", "app.ts", "typescript", known, ts_aliases=aliases)
    assert resolved == "src/lib/foo.ts"


def test_dependency_graph_picks_up_alias_edge():
    project = ProjectContext(
        name="frontend",
        root="/tmp/frontend",
        files=[
            _f("tsconfig.json", '{"compilerOptions":{"baseUrl":".","paths":{"@/*":["src/*"]}}}', "json"),
            _f("src/main.tsx", 'import { useFoo } from "@/lib/foo";\n', "tsx"),
            _f("src/lib/foo.ts", 'export const useFoo = () => 1;\n', "typescript"),
        ],
    )
    graph = DependencyGraph.build_from_project(project)
    assert graph.graph.has_edge("src/main.tsx", "src/lib/foo.ts")
