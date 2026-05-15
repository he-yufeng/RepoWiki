"""orchestrates the multi-step LLM analysis pipeline."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from repowiki.core.cache import Cache, content_hash
from repowiki.core.models import (
    ArchitectureDiagram,
    FileInfo,
    ModuleDoc,
    ProjectContext,
    ProjectOverview,
    ReadingGuide,
    WikiData,
)
from repowiki.llm.client import LLMClient, LLMError
from repowiki.llm.prompts import (
    build_architecture_prompt,
    build_module_prompt,
    build_overview_prompt,
    build_reading_guide_prompt,
    extract_json,
)

logger = logging.getLogger(__name__)


def _approx_tokens(text: str) -> int:
    """rough token count. uses tiktoken cl100k if available, else chars/4."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)


class Analyzer:
    """runs the full wiki generation pipeline."""

    def __init__(
        self,
        llm: LLMClient,
        cache: Cache,
        language: str = "en",
        concurrency: int = 5,
        max_context_tokens: int = 32_000,
    ):
        self.llm = llm
        self.cache = cache
        self.language = language
        self.max_context_tokens = max_context_tokens
        self._sem = asyncio.Semaphore(concurrency)
        self._on_progress: Callable[[str], None] | None = None
        self.errors: list[str] = []

    def _report_error(self, where: str, exc: Exception) -> None:
        msg = f"{where} failed: {exc}"
        self.errors.append(msg)
        logger.warning(msg)
        if self._on_progress:
            self._on_progress(f"[error] {msg}")

    async def analyze(
        self,
        project: ProjectContext,
        on_progress: Callable[[str], None] | None = None,
    ) -> WikiData:
        """run the full analysis pipeline and return WikiData."""
        self._on_progress = on_progress
        self.errors = []

        def progress(msg: str):
            if on_progress:
                on_progress(msg)

        # 1. prepare context
        progress("Preparing file context...")
        key_files_text = self._build_key_files_context(project)
        # structure_hash captures only the project shape (paths + sizes), so
        # editing the body of a single source file doesn't invalidate the
        # arch / guide passes. overview_hash also folds in README / pyproject
        # because those genuinely change the elevator pitch.
        structure_hash = self._structure_hash(project)
        overview_hash = self._overview_hash(project, structure_hash)

        # 2. generate overview
        progress("Generating project overview...")
        overview = await self._generate_overview(project, key_files_text, overview_hash)

        # 3. group files into modules and analyze each
        modules_map = self._group_into_modules(project.files)
        progress(f"Analyzing {len(modules_map)} modules...")
        module_docs = await self._analyze_modules(
            modules_map, overview.one_liner, project, progress
        )

        # 4. generate architecture diagram
        progress("Detecting architecture...")
        architecture = await self._generate_architecture(project, key_files_text, structure_hash)

        # 5. generate reading guide (needs module summaries + rankings placeholder)
        progress("Creating reading guide...")
        reading_guide = await self._generate_reading_guide(
            project, module_docs, structure_hash
        )

        progress("Done!")
        return WikiData(
            overview=overview,
            modules=module_docs,
            architecture=architecture,
            reading_guide=reading_guide,
        )

    @staticmethod
    def _structure_hash(project: ProjectContext) -> str:
        """hash that captures project shape only (paths + sizes), not file bodies."""
        parts = sorted(f"{f.path}:{f.size}" for f in project.files)
        return content_hash("\n".join(parts))

    @staticmethod
    def _overview_hash(project: ProjectContext, structure_hash: str) -> str:
        """structure hash + content hash of README / pyproject / package.json -- the
        files that actually change a project's elevator pitch."""
        relevant = ("readme", "pyproject", "package.json", "cargo.toml", "go.mod")
        bodies = []
        for f in project.files:
            name = f.path.lower()
            if any(token in name for token in relevant):
                bodies.append((f.path, f.content or f.preview or ""))
        bodies.sort()
        material = structure_hash + "|" + "|".join(f"{p}:{c}" for p, c in bodies)
        return content_hash(material)

    def _build_key_files_context(self, project: ProjectContext) -> str:
        """collect config files and entrypoints for the overview prompt.

        Files are added in priority order (config > entrypoint > pagerank
        in the dependency graph) until ``max_context_tokens`` is exhausted.
        Each file body is itself capped at 4 KB. Token counting uses tiktoken
        if available, otherwise the cheap chars/4 estimate.
        """
        candidates = [f for f in project.files if f.is_config or f.is_entrypoint]
        ordered = self._order_by_importance(candidates, project)

        budget = self.max_context_tokens
        parts: list[str] = []
        used = 0
        for f in ordered:
            content = f.content if f.content else f.preview
            if len(content) > 4096:
                content = content[:4096] + "\n... (truncated)"
            block = f"### {f.path}\n```{f.language}\n{content}\n```"
            cost = _approx_tokens(block)
            if budget and used + cost > budget:
                # try to fit a short stub so the LLM at least knows the file exists
                stub = f"### {f.path}\n(skipped to fit context budget)\n"
                stub_cost = _approx_tokens(stub)
                if used + stub_cost <= budget:
                    parts.append(stub)
                    used += stub_cost
                continue
            parts.append(block)
            used += cost
        return "\n\n".join(parts)

    @staticmethod
    def _order_by_importance(
        candidates: list[FileInfo], project: ProjectContext
    ) -> list[FileInfo]:
        """sort: config files first, then entrypoints, then by PageRank."""
        # lazy import: graph depends on networkx, only need it here
        from repowiki.core.graph import DependencyGraph

        try:
            graph = DependencyGraph.build_from_project(project)
            pagerank = dict(graph.rank_files())
        except Exception:
            pagerank = {}

        def key(f: FileInfo) -> tuple:
            tier = 0 if f.is_config else (1 if f.is_entrypoint else 2)
            # negative pagerank so larger scores sort first
            return (tier, -pagerank.get(f.path, 0.0), f.path)

        return sorted(candidates, key=key)

    async def _generate_overview(
        self, project: ProjectContext, key_files: str, tree_hash: str
    ) -> ProjectOverview:
        cache_key = f"overview:{tree_hash}"
        cached = await self.cache.get(cache_key)
        if cached:
            try:
                return ProjectOverview(**cached)
            except Exception:
                pass

        messages = build_overview_prompt(project.file_tree, key_files, self.language)
        try:
            raw = await self.llm.complete(messages, max_tokens=4096)
        except LLMError as e:
            self._report_error("overview", e)
            return ProjectOverview(name=project.name)

        data = extract_json(raw)
        if not data or not isinstance(data, dict):
            logger.warning("Failed to parse overview JSON, using defaults")
            return ProjectOverview(name=project.name)

        filtered = {k: v for k, v in data.items() if k in ProjectOverview.model_fields}
        try:
            overview = ProjectOverview(**filtered)
        except Exception:
            overview = ProjectOverview(name=project.name)
        await self.cache.put(cache_key, overview.model_dump())
        return overview

    def _group_into_modules(self, files: list[FileInfo]) -> dict[str, list[FileInfo]]:
        """group files by their top-level directory."""
        from pathlib import Path

        modules: dict[str, list[FileInfo]] = {}
        for f in files:
            parts = Path(f.path).parts
            if len(parts) == 1:
                # root-level files go into a "root" module
                modules.setdefault("root", []).append(f)
            else:
                # use the first directory as module name
                mod = parts[0]
                # if it's a common wrapper like "src", use the second level
                if mod in ("src", "lib", "pkg", "internal", "app") and len(parts) > 2:
                    mod = parts[1]
                modules.setdefault(mod, []).append(f)
        return modules

    async def _analyze_modules(
        self,
        modules: dict[str, list[FileInfo]],
        project_summary: str,
        project: ProjectContext,
        progress: Callable[[str], None],
    ) -> list[ModuleDoc]:
        tasks = []
        for name, files in modules.items():
            tasks.append(self._analyze_one_module(name, files, project_summary, project))

        results = []
        for i, coro in enumerate(asyncio.as_completed(tasks)):
            doc = await coro
            if doc:
                results.append(doc)
            progress(f"Analyzed module {i + 1}/{len(tasks)}")

        # sort by number of files (largest first)
        results.sort(key=lambda m: -len(m.files))
        return results

    async def _analyze_one_module(
        self,
        name: str,
        files: list[FileInfo],
        project_summary: str,
        project: ProjectContext,
    ) -> ModuleDoc | None:
        async with self._sem:
            # build context for this module
            files_text_parts = []
            content_parts = []
            for f in files:
                content = f.content if f.content else f.preview
                if len(content) > 4096:
                    content = content[:4096] + "\n... (truncated)"
                files_text_parts.append(f"### {f.path} ({f.language})\n```{f.language}\n{content}\n```")
                content_parts.append(content)

            files_context = "\n\n".join(files_text_parts)
            cache_key = f"module:{name}:{content_hash(''.join(content_parts))}"

            cached = await self.cache.get(cache_key)
            if cached:
                try:
                    return ModuleDoc(**cached)
                except Exception:
                    pass

            messages = build_module_prompt(name, files_context, project_summary, self.language)
            try:
                raw = await self.llm.complete(messages, max_tokens=4096)
            except LLMError as e:
                self._report_error(f"module {name!r}", e)
                return ModuleDoc(
                    name=name,
                    purpose=f"Module containing {len(files)} files (analysis skipped: {e})",
                )

            data = extract_json(raw)
            if not data or not isinstance(data, dict):
                logger.warning("Failed to parse module '%s' JSON", name)
                return ModuleDoc(name=name, purpose=f"Module containing {len(files)} files")

            # ensure name is present (LLM sometimes omits it)
            data.setdefault("name", name)
            filtered = {k: v for k, v in data.items() if k in ModuleDoc.model_fields}
            try:
                doc = ModuleDoc(**filtered)
            except Exception:
                doc = ModuleDoc(name=name, purpose=data.get("purpose", ""))
            await self.cache.put(cache_key, doc.model_dump())
            return doc

    async def _generate_architecture(
        self, project: ProjectContext, key_files: str, tree_hash: str
    ) -> ArchitectureDiagram:
        cache_key = f"arch:{tree_hash}"
        cached = await self.cache.get(cache_key)
        if cached:
            try:
                return ArchitectureDiagram(**cached)
            except Exception:
                pass

        messages = build_architecture_prompt(project.file_tree, key_files, self.language)
        try:
            raw = await self.llm.complete(messages, max_tokens=4096)
        except LLMError as e:
            self._report_error("architecture", e)
            return ArchitectureDiagram()

        data = extract_json(raw)
        if not data or not isinstance(data, dict):
            logger.warning("Failed to parse architecture JSON")
            return ArchitectureDiagram()

        filtered = {k: v for k, v in data.items() if k in ArchitectureDiagram.model_fields}
        try:
            arch = ArchitectureDiagram(**filtered)
        except Exception:
            arch = ArchitectureDiagram()
        await self.cache.put(cache_key, arch.model_dump())
        return arch

    async def _generate_reading_guide(
        self,
        project: ProjectContext,
        module_docs: list[ModuleDoc],
        tree_hash: str,
    ) -> ReadingGuide:
        cache_key = f"guide:{tree_hash}"
        cached = await self.cache.get(cache_key)
        if cached:
            try:
                return ReadingGuide(**cached)
            except Exception:
                pass

        # build rankings placeholder (will be replaced by PageRank in Phase 3)
        rankings_parts = []
        for i, f in enumerate(project.files[:20], 1):
            tag = ""
            if f.is_entrypoint:
                tag = " [entrypoint]"
            elif f.is_config:
                tag = " [config]"
            rankings_parts.append(f"{i}. {f.path}{tag} ({f.lines} lines)")
        rankings = "\n".join(rankings_parts)

        module_parts = []
        for m in module_docs:
            module_parts.append(f"- **{m.name}**: {m.purpose}")
        module_summaries = "\n".join(module_parts)

        messages = build_reading_guide_prompt(rankings, module_summaries, self.language)
        try:
            raw = await self.llm.complete(messages, max_tokens=4096)
        except LLMError as e:
            self._report_error("reading-guide", e)
            return ReadingGuide()

        data = extract_json(raw)
        if not data or not isinstance(data, dict):
            logger.warning("Failed to parse reading guide JSON")
            return ReadingGuide()

        filtered = {k: v for k, v in data.items() if k in ReadingGuide.model_fields}
        try:
            guide = ReadingGuide(**filtered)
        except Exception:
            guide = ReadingGuide()
        await self.cache.put(cache_key, guide.model_dump())
        return guide
