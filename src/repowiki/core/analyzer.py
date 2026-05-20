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
    build_repair_prompt,
    extract_json,
    missing_required_keys,
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


def _approx_tokens_batch(texts: list[str]) -> list[int]:
    """token-count a batch of texts in one call.

    Loads the tiktoken encoding once and uses :meth:`encode_batch` (which is
    parallelised internally), instead of paying the encoding lookup +
    per-string Python overhead for every file. Falls back to ``chars // 4``
    when tiktoken isn't available, mirroring :func:`_approx_tokens`.
    """
    if not texts:
        return []
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        # encode_batch returns a list of token-id lists; we just need lengths.
        return [len(toks) for toks in enc.encode_batch(texts)]
    except Exception:
        return [max(1, len(t) // 4) for t in texts]


def _format_rankings(
    project: ProjectContext,
    rankings: list[tuple[str, float]] | None,
    top_n: int = 20,
) -> str:
    """render a markdown list of (rank, path, tag, lines) for the LLM.

    When ``rankings`` is provided we sort by PageRank score (largest first);
    otherwise we fall back to scan order so the prompt still has *something*
    but the LLM no longer sees a hand-wavy "top 20 files".
    """
    info_by_path = {f.path: f for f in project.files}
    if rankings:
        ordered_paths = [path for path, _ in rankings if path in info_by_path]
    else:
        ordered_paths = [f.path for f in project.files]

    parts: list[str] = []
    for i, path in enumerate(ordered_paths[:top_n], 1):
        f = info_by_path[path]
        tag = ""
        if f.is_entrypoint:
            tag = " [entrypoint]"
        elif f.is_config:
            tag = " [config]"
        parts.append(f"{i}. {path}{tag} ({f.lines} lines)")
    return "\n".join(parts)


def _module_summary_block(module_docs: list) -> str:
    """produce a stable text summary of the analyzed modules.

    Used both for the architecture prompt (instead of re-sending key_files)
    and for the reading-guide prompt. Output is sorted by name so the hash
    is deterministic across runs that complete tasks in different orders.
    """
    rows = sorted(
        ((m.name, m.purpose or "", len(m.files)) for m in module_docs),
        key=lambda r: r[0],
    )
    parts = [
        f"- **{name}** ({nfiles} file{'s' if nfiles != 1 else ''}): {purpose}"
        for name, purpose, nfiles in rows
    ]
    return "\n".join(parts)


class Analyzer:
    """runs the full wiki generation pipeline."""

    def __init__(
        self,
        llm: LLMClient,
        cache: Cache,
        language: str = "en",
        concurrency: int = 5,
        max_context_tokens: int = 32_000,
        changed_paths: set[str] | None = None,
    ):
        self.llm = llm
        self.cache = cache
        self.language = language
        self.max_context_tokens = max_context_tokens
        # if non-None, modules whose files all sit outside this set will skip
        # the LLM call entirely and rely on cache (or return a placeholder).
        # Set to None to disable incremental mode and analyse everything.
        self.changed_paths = changed_paths
        self._sem = asyncio.Semaphore(concurrency)
        self._on_progress: Callable[[str], None] | None = None
        self.errors: list[str] = []
        self.skipped_modules: list[str] = []

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
        rankings: list[tuple[str, float]] | None = None,
    ) -> WikiData:
        """run the full analysis pipeline and return WikiData.

        ``rankings`` is the PageRank-sorted list of (path, score) from
        :class:`DependencyGraph`. When supplied, the reading guide uses real
        importance ranks instead of scan order. The caller is expected to
        build the dependency graph once and pass it here.
        """
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

        # 4. generate architecture diagram. It now consumes the module
        # summaries instead of re-sending key_files -- those were already
        # spent on the overview pass.
        progress("Detecting architecture...")
        architecture = await self._generate_architecture(
            project, module_docs, structure_hash
        )

        # 5. generate reading guide using real PageRank when provided
        progress("Creating reading guide...")
        reading_guide = await self._generate_reading_guide(
            project, module_docs, structure_hash, rankings=rankings,
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
        Each file body is itself capped at 4 KB. Token counting batches every
        block through a single ``tiktoken.encode_batch`` call -- previously we
        re-encoded one file at a time, which dominated this function on large
        projects with many config/entrypoint files.
        """
        candidates = [f for f in project.files if f.is_config or f.is_entrypoint]
        ordered = self._order_by_importance(candidates, project)

        # Build every block up front, then token-count them in one batch.
        blocks: list[str] = []
        stubs: list[str] = []
        for f in ordered:
            content = f.content if f.content else f.preview
            if len(content) > 4096:
                content = content[:4096] + "\n... (truncated)"
            blocks.append(f"### {f.path}\n```{f.language}\n{content}\n```")
            stubs.append(f"### {f.path}\n(skipped to fit context budget)\n")

        block_costs = _approx_tokens_batch(blocks)
        stub_costs = _approx_tokens_batch(stubs)

        budget = self.max_context_tokens
        parts: list[str] = []
        used = 0
        for block, stub, cost, stub_cost in zip(blocks, stubs, block_costs, stub_costs):
            if budget and used + cost > budget:
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
        # one-shot repair when the first response missed required fields
        missing = missing_required_keys(data, ["name", "one_liner"])
        if missing:
            logger.info("overview JSON missing %s, asking for repair", missing)
            try:
                raw = await self.llm.complete(
                    build_repair_prompt(messages, raw or "", missing),
                    max_tokens=4096,
                )
                data = extract_json(raw) or data
            except LLMError as e:
                logger.warning("overview repair call failed: %s", e)

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

    def _group_into_modules(
        self,
        files: list[FileInfo],
        split_threshold: int = 10,
    ) -> dict[str, list[FileInfo]]:
        """group files by directory.

        Initial pass uses the top-level dir (skipping common wrappers like
        ``src``/``lib``). Any module that ends up with more than
        ``split_threshold`` files is recursively split by its next directory
        level so the LLM doesn't get a fire-hose of unrelated files in a
        single prompt.
        """
        from pathlib import Path

        # first pass: top-level grouping (existing behaviour)
        modules: dict[str, list[FileInfo]] = {}
        for f in files:
            parts = Path(f.path).parts
            if len(parts) == 1:
                modules.setdefault("root", []).append(f)
            else:
                mod = parts[0]
                if mod in ("src", "lib", "pkg", "internal", "app") and len(parts) > 2:
                    mod = parts[1]
                modules.setdefault(mod, []).append(f)

        # second pass: split oversize modules by their next directory level
        result: dict[str, list[FileInfo]] = {}
        for name, mod_files in modules.items():
            if len(mod_files) <= split_threshold:
                result[name] = mod_files
                continue
            sub = self._split_module(name, mod_files)
            # if the split degenerates back to one bucket, keep the original name
            if len(sub) <= 1:
                result[name] = mod_files
            else:
                for sub_name, sub_files in sub.items():
                    result[sub_name] = sub_files
        return result

    @staticmethod
    def _split_module(
        parent: str, files: list[FileInfo]
    ) -> dict[str, list[FileInfo]]:
        """split a module's files by their next path component after the
        directory the module already represents.

        Files that live directly under ``parent`` (no further directory)
        go into a ``parent/_root`` bucket.
        """
        from pathlib import Path

        buckets: dict[str, list[FileInfo]] = {}
        for f in files:
            parts = Path(f.path).parts
            try:
                idx = parts.index(parent)
            except ValueError:
                # synthetic parent ("root"): treat as if the file's first dir
                # is the next component
                idx = -1

            # the segment immediately after the parent dir; the final part is
            # always the filename, so we need at least one extra dir between.
            next_idx = idx + 1
            if next_idx >= len(parts) - 1:
                key = f"{parent}/_root"
            else:
                key = f"{parent}/{parts[next_idx]}"
            buckets.setdefault(key, []).append(f)
        return buckets

    @staticmethod
    def _build_module_context(
        name: str, files: list[FileInfo]
    ) -> tuple[str, str]:
        """assemble the LLM context + cache key for one module.

        Pure-synchronous CPU work (string joins + sha256). Designed to run on
        an executor in parallel with peer modules so the analyzer's main loop
        can enter the LLM stage as soon as the *first* context is ready.
        """
        files_text_parts: list[str] = []
        content_parts: list[str] = []
        for f in files:
            content = f.content if f.content else f.preview
            if len(content) > 4096:
                content = content[:4096] + "\n... (truncated)"
            files_text_parts.append(
                f"### {f.path} ({f.language})\n```{f.language}\n{content}\n```"
            )
            content_parts.append(content)

        files_context = "\n\n".join(files_text_parts)
        cache_key = f"module:{name}:{content_hash(''.join(content_parts))}"
        return files_context, cache_key

    async def _analyze_modules(
        self,
        modules: dict[str, list[FileInfo]],
        project_summary: str,
        project: ProjectContext,
        progress: Callable[[str], None],
    ) -> list[ModuleDoc]:
        # Pre-build every module's context concurrently in the default
        # executor. Before this change, each call to ``_analyze_one_module``
        # did the string concat + content_hash inline (synchronously) before
        # touching the LLM; with N modules that was N sequential prep passes.
        loop = asyncio.get_event_loop()
        items = list(modules.items())
        contexts = await asyncio.gather(*[
            loop.run_in_executor(None, self._build_module_context, name, files)
            for name, files in items
        ])

        tasks = [
            self._analyze_one_module(name, files, ctx, project_summary)
            for (name, files), ctx in zip(items, contexts)
        ]

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
        ctx: tuple[str, str],
        project_summary: str,
    ) -> ModuleDoc | None:
        files_context, cache_key = ctx

        # Cache lookup is async (sqlite) but very cheap -- outside the
        # semaphore so an entirely cached run incurs zero serialization.
        cached = await self.cache.get(cache_key)
        if cached:
            try:
                return ModuleDoc(**cached)
            except Exception:
                pass

        # Incremental mode: skip the LLM entirely for unchanged modules.
        if self.changed_paths is not None:
            module_paths = {f.path for f in files}
            if module_paths.isdisjoint(self.changed_paths):
                self.skipped_modules.append(name)
                if self._on_progress:
                    self._on_progress(f"[skip] module {name!r} unchanged")
                return ModuleDoc(
                    name=name,
                    purpose=f"Module containing {len(files)} files (skipped, unchanged since prior run)",
                )

        messages = build_module_prompt(name, files_context, project_summary, self.language)

        # The semaphore now only covers the actual provider call, so
        # --concurrency=5 really means five concurrent LLM requests.
        async with self._sem:
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
        self,
        project: ProjectContext,
        module_docs: list[ModuleDoc],
        tree_hash: str,
    ) -> ArchitectureDiagram:
        # cache key folds in module summaries so re-running with different
        # module analyses (e.g. after --since invalidates some) doesn't
        # silently return stale arch JSON.
        module_summary_text = _module_summary_block(module_docs)
        summary_hash = content_hash(module_summary_text)
        # v3: prompt no longer carries file_tree, so old v2 entries reflect a
        # different prompt shape -- bump the key to force a clean recompute.
        cache_key = f"arch:v3:{tree_hash}:{summary_hash}"
        cached = await self.cache.get(cache_key)
        if cached:
            try:
                return ArchitectureDiagram(**cached)
            except Exception:
                pass

        messages = build_architecture_prompt(
            project.file_tree, module_summary_text, self.language
        )
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
        *,
        rankings: list[tuple[str, float]] | None = None,
    ) -> ReadingGuide:
        rankings_text = _format_rankings(project, rankings)
        # v2 cache key folds in the rankings so the guide is recomputed when
        # PageRank shifts (e.g. after a refactor that re-routes imports).
        ranking_hash = content_hash(rankings_text)
        cache_key = f"guide:v2:{tree_hash}:{ranking_hash}"
        cached = await self.cache.get(cache_key)
        if cached:
            try:
                return ReadingGuide(**cached)
            except Exception:
                pass

        module_summaries = _module_summary_block(module_docs)

        messages = build_reading_guide_prompt(rankings_text, module_summaries, self.language)
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
