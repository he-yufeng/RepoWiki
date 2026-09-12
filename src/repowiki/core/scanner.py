"""scan a project directory and collect file metadata for analysis."""

from __future__ import annotations

import logging
import os
from fnmatch import fnmatch
from pathlib import Path

from repowiki.core.models import FileInfo, ScanReport

logger = logging.getLogger(__name__)

_SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".idea", ".vscode", ".next", "dist", "build", ".tox", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "egg-info", ".turbo", "coverage",
    ".cache", "vendor", "target", "__snapshots__", ".svn", ".hg",
    ".gradle", ".m2", "Pods", ".dart_tool", ".pub-cache",
}

_SKIP_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv", ".flac",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".xz",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".dat",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".pyc", ".pyo", ".class", ".o", ".obj",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".db", ".sqlite", ".sqlite3",
    ".lock",
    ".min.js", ".min.css",
    ".map",
    ".wasm",
}

_SENSITIVE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".npmrc",
    ".pypirc",
    ".netrc",
    "id_rsa",
    "id_ed25519",
    "known_hosts",
}

_MINIFIED_SOURCE_EXTS = {".js", ".mjs", ".cjs", ".css"}

_LANG_MAP = {
    ".py": "python", ".pyi": "python",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".mts": "typescript",
    ".jsx": "jsx", ".tsx": "tsx",
    ".html": "html", ".htm": "html",
    ".css": "css", ".scss": "scss", ".less": "less",
    ".json": "json", ".jsonc": "json",
    ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown", ".mdx": "markdown",
    ".txt": "text", ".rst": "rst",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin", ".kts": "kotlin",
    ".scala": "scala",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".hpp": "cpp", ".cc": "cpp", ".cxx": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".r": "r", ".R": "r",
    ".sql": "sql",
    ".swift": "swift",
    ".lua": "lua",
    ".dart": "dart",
    ".vue": "vue",
    ".svelte": "svelte",
    ".zig": "zig",
    ".nim": "nim",
    ".ex": "elixir", ".exs": "elixir",
    ".erl": "erlang",
    ".hs": "haskell",
    ".ml": "ocaml",
    ".clj": "clojure",
    ".proto": "protobuf",
    ".graphql": "graphql", ".gql": "graphql",
    ".tf": "terraform", ".hcl": "hcl",
    ".prisma": "prisma",
    ".astro": "astro",
    ".cfg": "ini", ".ini": "ini",
    ".env": "text",
    ".cmake": "cmake",
    ".gradle": "gradle",
    ".dockerfile": "dockerfile",
}

# languages that carry the dependency structure of a repo; docs and assets
# only get file-cap budget after these are safe
_CODE_LANGS = frozenset({
    "python", "javascript", "typescript", "jsx", "tsx", "go", "rust", "java",
    "kotlin", "scala", "c", "cpp", "csharp", "ruby", "php", "r", "sql",
    "swift", "lua", "dart", "vue", "svelte", "zig", "shell", "dockerfile",
    "makefile",
})

# files that give the LLM project context -- always read in full
_CONFIG_FILES = {
    "requirements.txt", "setup.py", "setup.cfg", "pyproject.toml",
    "package.json", "Cargo.toml", "go.mod", "go.sum",
    "Makefile", "CMakeLists.txt",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example", "config.py", "config.yaml", "config.json", "config.toml",
    "README.md", "README.rst", "README.txt", "README",
    "tsconfig.json", "vite.config.ts", "vite.config.js",
    "webpack.config.js", "rollup.config.js",
    "Gemfile", "build.gradle", "pom.xml",
    ".eslintrc.json", ".prettierrc",
}

# files that are likely entry points
_ENTRYPOINT_NAMES = {
    "main.py", "app.py", "index.py", "server.py", "run.py", "__main__.py",
    "main.go", "main.rs", "main.ts", "main.js",
    "index.ts", "index.js", "index.tsx", "index.jsx",
    "App.tsx", "App.jsx", "App.vue", "App.svelte",
    "manage.py", "wsgi.py", "asgi.py",
}

_ENTRYPOINT_DIRS = {"cmd", "bin", "scripts", "entrypoints"}


def _is_binary(data: bytes) -> bool:
    return b"\x00" in data[:1024]


def _has_skipped_suffix(path: Path) -> bool:
    name = path.name.lower()
    return any(name.endswith(ext) for ext in _SKIP_EXTS)


class IgnoreRules:
    def __init__(self, patterns: list[tuple[str, bool]]):
        self.patterns = patterns

    @classmethod
    def from_root(cls, root: Path) -> "IgnoreRules":
        patterns: list[tuple[str, bool]] = []
        for name in (".gitignore", ".repowikiignore"):
            path = root / name
            if not path.exists():
                continue
            for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                negated = line.startswith("!")
                if negated:
                    line = line[1:].strip()
                if line:
                    patterns.append((line.replace("\\", "/"), negated))
        return cls(patterns)

    def matches(self, rel_path: str, *, is_dir: bool = False) -> bool:
        rel_path = rel_path.replace("\\", "/").strip("/")
        ignored = False
        for pattern, negated in self.patterns:
            if _matches_ignore_pattern(pattern, rel_path, is_dir=is_dir):
                ignored = not negated
        return ignored


def _matches_ignore_pattern(pattern: str, rel_path: str, *, is_dir: bool) -> bool:
    dir_pattern = pattern.endswith("/")
    pattern = pattern.strip("/")
    if not pattern:
        return False
    if dir_pattern:
        return is_dir and (rel_path == pattern or rel_path.startswith(pattern + "/"))
    if "/" in pattern:
        return fnmatch(rel_path, pattern) or rel_path.startswith(pattern.rstrip("*") + "/")
    return any(fnmatch(part, pattern) for part in rel_path.split("/"))


def _is_sensitive_name(path: Path) -> bool:
    name = path.name.lower()
    if name in _SENSITIVE_NAMES:
        return True
    return name.startswith(".env.") and name != ".env.example"


def _looks_minified_source(path: str, text: str) -> bool:
    if Path(path).suffix.lower() not in _MINIFIED_SOURCE_EXTS:
        return False

    lines = text.splitlines() or [text]
    longest = max(len(line) for line in lines)
    if longest < 1000:
        return False

    non_empty = [line for line in lines if line.strip()]
    return len(non_empty) <= 5 or longest > len(text) * 0.5


def detect_language(path: str) -> str:
    name = Path(path).name.lower()
    if name == "dockerfile" or name.startswith("dockerfile."):
        return "dockerfile"
    if name == "makefile":
        return "makefile"
    ext = Path(path).suffix.lower()
    return _LANG_MAP.get(ext, "unknown")


def _is_entrypoint(rel_path: str) -> bool:
    parts = Path(rel_path).parts
    name = parts[-1]
    if name in _ENTRYPOINT_NAMES:
        return True
    if len(parts) >= 2 and parts[-2] in _ENTRYPOINT_DIRS:
        return True
    return False


def build_file_tree(files: list[FileInfo], max_lines: int = 200) -> str:
    """render an ascii tree from the file list, similar to `tree` command."""
    # collect unique directories + files
    entries: set[str] = set()
    for f in files:
        entries.add(f.path)
        parts = Path(f.path).parts
        for i in range(1, len(parts)):
            entries.add(str(Path(*parts[:i])) + "/")

    sorted_entries = sorted(entries)
    lines = []
    for entry in sorted_entries[:max_lines]:
        depth = entry.rstrip("/").count(os.sep)
        indent = "  " * depth
        name = Path(entry.rstrip("/")).name
        if entry.endswith("/"):
            name += "/"
        lines.append(f"{indent}{name}")

    if len(sorted_entries) > max_lines:
        lines.append(f"  ... and {len(sorted_entries) - max_lines} more entries")
    return "\n".join(lines)


def scan_directory(
    root: str | Path,
    max_file_size: int = 200 * 1024,
    max_files: int = 1000,
    preview_lines: int = 80,
    report: ScanReport | None = None,
) -> list[FileInfo]:
    """walk a project directory and return file info with previews.

    When a ScanReport is passed it is filled with the coverage story: how many
    candidate files existed, how many were kept, and what was dropped and why.
    """
    root = Path(root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Not a directory: {root}")

    results: list[FileInfo] = []
    ignore_rules = IgnoreRules.from_root(root)

    # the walk only stops at this hard ceiling; the real max_files budget is
    # applied by priority after the walk
    hard_cap = max(max_files * 4, max_files + 100)

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        kept_dirs = []
        for dirname in dirnames:
            full_dir = Path(dirpath) / dirname
            rel_dir = full_dir.relative_to(root).as_posix()
            if dirname in _SKIP_DIRS or dirname.endswith(".egg-info"):
                if report is not None:
                    report.skipped_dirs.append(rel_dir)
                continue
            if ignore_rules.matches(rel_dir, is_dir=True):
                if report is not None:
                    report.skipped_dirs.append(rel_dir)
                continue
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for fname in filenames:
            if len(results) >= hard_cap:
                logger.info("Hit hard scan cap (%d), stopping", hard_cap)
                break

            full = Path(dirpath) / fname
            rel = str(full.relative_to(root))
            rel_posix = full.relative_to(root).as_posix()

            if full.is_symlink():
                continue

            if ignore_rules.matches(rel_posix):
                continue

            if _is_sensitive_name(full):
                continue

            if _has_skipped_suffix(full):
                continue

            if report is not None:
                report.candidates += 1

            try:
                size = full.stat().st_size
            except OSError:
                continue
            if size > max_file_size or size == 0:
                if report is not None and size > max_file_size:
                    report.oversized_count += 1
                    if len(report.oversized) < 3:
                        report.oversized.append(rel_posix)
                continue

            try:
                raw = full.read_bytes()
            except OSError:
                continue
            if _is_binary(raw):
                if report is not None:
                    report.binary_count += 1
                continue

            try:
                text = raw.decode("utf-8", errors="replace")
            except Exception:
                continue

            if _looks_minified_source(rel, text):
                if report is not None:
                    report.minified_count += 1
                continue

            lang = detect_language(rel)
            is_cfg = fname in _CONFIG_FILES
            is_entry = _is_entrypoint(rel)
            line_count = text.count("\n") + 1

            # config/entrypoint files get full content for better LLM context
            if is_cfg or is_entry:
                preview = text
            else:
                preview = "\n".join(text.splitlines()[:preview_lines])

            results.append(FileInfo(
                path=rel,
                size=size,
                language=lang,
                lines=line_count,
                preview=preview,
                content=text,
                is_config=is_cfg,
                is_entrypoint=is_entry,
            ))

        if len(results) >= hard_cap:
            break

    # cap by priority, not walk order: on docs-heavy repos the plain walk
    # fills the budget with markdown before the source tree is reached
    if len(results) > max_files:
        keep = sorted(
            range(len(results)),
            key=lambda i: (
                0 if results[i].is_config or results[i].is_entrypoint
                else 1 if results[i].language in _CODE_LANGS
                else 2,
                i,
            ),
        )[:max_files]
        dropped = len(results) - len(keep)
        results = [results[i] for i in sorted(keep)]
        if report is not None:
            report.priority_dropped = dropped
        logger.info(
            "File cap (%d) hit; kept configs/entrypoints/code first, dropped %d lower-priority files",
            max_files,
            dropped,
        )

    if report is not None:
        report.kept = len(results)

    # sort: configs first, then entrypoints, then alphabetical
    def _sort_key(f: FileInfo) -> tuple:
        if f.is_config:
            return (0, f.path)
        if f.is_entrypoint:
            return (1, f.path)
        return (2, f.path)

    results.sort(key=_sort_key)
    return results
