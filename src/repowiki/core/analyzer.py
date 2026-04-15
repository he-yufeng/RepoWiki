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
from repowiki.llm.client import LLMClient
from repowiki.llm.prompts import (
    build_architecture_prompt,
    build_module_prompt,
    build_overview_prompt,
    build_reading_guide_prompt,
    extract_json,
)

logger = logging.getLogger(__name__)


class Analyzer:
    """runs the full wiki generation pipeline."""

    def __init__(
        self,
        llm: LLMClient,
        cache: Cache,
        language: str = "en",
        concurrency: int = 5,
    ):
        self.llm = llm
        self.cache = cache
        self.language = language
        self._sem = asyncio.Semaphore(concurrency)

    async def analyze(
        self,
        project: ProjectContext,
        on_progress: Callable[[str], None] | None = None,
    ) -> WikiData:
        """run the full analysis pipeline and return WikiData."""

        def progress(msg: str):
            if on_progress:
                on_progress(msg)

        # 1. prepare context
        progress("Preparing file context...")
        key_files_text = self._build_key_files_context(project)
        tree_hash = content_hash(project.file_tree + key_files_text)

        # 2. generate overview
        progress("Generating project overview...")
        overview = await self._generate_overview(project, key_files_text, tree_hash)

        # 3. group files into modules and analyze each
        modules_map = self._group_into_modules(project.files)
        progress(f"Analyzing {len(modules_map)} modules...")
        module_docs = await self._analyze_modules(
            modules_map, overview.one_liner, project, progress
        )

        # 4. generate architecture diagram
        progress("Detecting architecture...")
        architecture = await self._generate_architecture(project, key_files_text, tree_hash)

        # 5. generate reading guide (needs module summaries + rankings placeholder)
        progress("Creating reading guide...")
        reading_guide = await self._generate_reading_guide(
            project, module_docs, tree_hash
        )

        progress("Done!")
        return WikiData(
            overview=overview,
            modules=module_docs,
            architecture=architecture,
            reading_guide=reading_guide,
        )

    def _build_key_files_context(self, project: ProjectContext) -> str:
        """collect config files and entrypoints for the overview prompt."""
        parts = []
        for f in project.files:
            if f.is_config or f.is_entrypoint:
                content = f.content if f.content else f.preview
                # truncate large files
                if len(content) > 4096:
                    content = content[:4096] + "\n... (truncated)"
                parts.append(f"### {f.path}\n```{f.language}\n{content}\n```")
        return "\n\n".join(parts)

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
        raw = await self.llm.complete(messages, max_tokens=4096)
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
            raw = await self.llm.complete(messages, max_tokens=4096)
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
        raw = await self.llm.complete(messages, max_tokens=4096)
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
        raw = await self.llm.complete(messages, max_tokens=4096)
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
