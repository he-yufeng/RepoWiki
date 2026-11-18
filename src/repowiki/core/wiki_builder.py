"""assemble wiki pages from analysis results."""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass, field
from itertools import groupby

from repowiki.core.churn import file_churn, module_hotspots
from repowiki.core.graph import DependencyGraph, _get_module
from repowiki.core.models import ProjectContext, WikiData


@dataclass
class WikiPage:
    id: str
    title: str
    content: str
    parent_id: str = ""
    order: int = 0


@dataclass
class ModuleCard:
    """one structured knowledge card per module.

    The markdown cards page renders from this same list, so the web cards view
    and the exported wiki never drift (#10).
    """

    name: str
    purpose: str = ""
    file_count: int = 0
    key_symbols: list[str] = field(default_factory=list)
    extra_symbols: int = 0
    key_concepts: list[str] = field(default_factory=list)
    entry_files: list[str] = field(default_factory=list)
    extra_entries: int = 0
    in_cycle: bool = False
    hotspots: list[tuple[str, int]] = field(default_factory=list)
    relationships: list[tuple[str, str]] = field(default_factory=list)
    page_id: str = ""


@dataclass
class SymbolEntry:
    """one symbol in the structured and Markdown indexes."""

    name: str
    kind: str
    description: str
    module: str
    page_id: str


@dataclass
class SidebarItem:
    title: str
    page_id: str
    children: list[SidebarItem] = field(default_factory=list)


@dataclass
class Wiki:
    pages: list[WikiPage] = field(default_factory=list)
    sidebar: list[SidebarItem] = field(default_factory=list)
    project_name: str = ""
    cards: list[ModuleCard] = field(default_factory=list)
    symbols: list[SymbolEntry] = field(default_factory=list)

    def get_page(self, page_id: str) -> WikiPage | None:
        for p in self.pages:
            if p.id == page_id:
                return p
        return None


class WikiBuilder:
    """constructs a Wiki from analysis results."""

    def build(
        self,
        project: ProjectContext,
        wiki_data: WikiData,
        graph: DependencyGraph,
    ) -> Wiki:
        pages: list[WikiPage] = []
        sidebar: list[SidebarItem] = []

        # 1. index / overview page
        overview = wiki_data.overview
        overview_md = self._build_overview_page(overview, project)
        pages.append(WikiPage(id="index", title="Overview", content=overview_md, order=0))
        sidebar.append(SidebarItem(title="Overview", page_id="index"))

        # 2. architecture page
        arch = wiki_data.architecture
        if arch.architecture_type:
            arch_md = self._build_architecture_page(arch)
            pages.append(
                WikiPage(id="architecture", title="Architecture", content=arch_md, order=1)
            )
            sidebar.append(SidebarItem(title="Architecture", page_id="architecture"))

        # 2b. knowledge cards: one compact card per module, for choosing where
        # to start before opening a full page. The structured list is computed
        # once and kept on the wiki object; the markdown page renders from it.
        cards = self._collect_cards(wiki_data, graph, project.root)
        if cards:
            wiki_cards_md = self._build_cards_page(cards)
            pages.append(
                WikiPage(id="cards", title="Knowledge Cards", content=wiki_cards_md, order=2)
            )
            sidebar.append(SidebarItem(title="Knowledge Cards", page_id="cards"))

        # 2c. test map: which test files import which source files, plus the
        # files nothing imports; deterministic, like the call/data-flow views
        testmap_md = self._build_testmap_page(project)
        if testmap_md:
            pages.append(WikiPage(id="tests", title="Test Map", content=testmap_md, order=3))
            sidebar.append(SidebarItem(title="Test Map", page_id="tests"))

        # 3. module pages
        module_sidebar = SidebarItem(title="Modules", page_id="", children=[])
        for i, mod in enumerate(wiki_data.modules):
            mod_id = f"modules/{mod.name}"
            mod_md = self._build_module_page(mod)
            pages.append(
                WikiPage(
                    id=mod_id,
                    title=mod.name,
                    content=mod_md,
                    parent_id="modules",
                    order=i,
                )
            )
            module_sidebar.children.append(SidebarItem(title=mod.name, page_id=mod_id))
        if module_sidebar.children:
            sidebar.append(module_sidebar)

        # 4. reading guide
        guide = wiki_data.reading_guide
        if guide.steps:
            guide_md = self._build_reading_guide_page(guide)
            pages.append(
                WikiPage(id="reading-guide", title="Reading Guide", content=guide_md, order=10)
            )
            sidebar.append(SidebarItem(title="Reading Guide", page_id="reading-guide"))

        # 5. dependency graph
        mermaid = graph.to_mermaid()
        if mermaid:
            dep_md = self._build_dependency_page(graph, mermaid)
            pages.append(
                WikiPage(id="dependencies", title="Dependencies", content=dep_md, order=11)
            )
            sidebar.append(SidebarItem(title="Dependencies", page_id="dependencies"))

        # 6. symbol index: the structured entries and Markdown share one list
        symbols = self._collect_symbols(wiki_data)
        symbols_md = self._build_symbol_index_page(symbols)
        if symbols_md:
            pages.append(WikiPage(id="symbols", title="Symbol Index", content=symbols_md, order=12))
            sidebar.append(SidebarItem(title="Symbol Index", page_id="symbols"))

        self._link_pages(pages, wiki_data)
        return Wiki(
            pages=pages,
            sidebar=sidebar,
            project_name=project.name,
            cards=cards,
            symbols=symbols,
        )

    def _link_pages(self, pages: list[WikiPage], wiki_data: WikiData) -> None:
        # index exact symbol names and file paths to the module page owning them;
        # when several pages claim the same name the first one wins
        symbols: dict[str, str] = {}
        files: dict[str, str] = {}
        for mod in wiki_data.modules:
            page_id = f"modules/{mod.name}"
            for f in mod.files:
                files.setdefault(f.path, page_id)
                for s in f.key_symbols:
                    symbols.setdefault(s.name, page_id)
        if not symbols and not files:
            return
        for page in pages:
            page.content = _apply_cross_links(page.content, page.id, symbols, files)

    def _build_overview_page(self, overview, project) -> str:
        lines = [f"# {overview.name or project.name}\n"]
        if overview.one_liner:
            lines.append(f"> {overview.one_liner}\n")
        if overview.description:
            lines.append(f"{overview.description}\n")

        if project.coverage is not None and project.coverage.partial:
            cov = project.coverage
            note = f"> **Partial coverage:** this wiki was built from {cov.summary_line()}."
            if cov.oversized:
                note += (
                    " Oversized files left out: " + ", ".join(f"`{p}`" for p in cov.oversized) + "."
                )
            if cov.skipped_dirs:
                note += (
                    " Excluded directories: "
                    + ", ".join(f"`{d}`" for d in cov.skipped_dirs[:5])
                    + "."
                )
            lines.append(note + " Pages below describe only the scanned subset.\n")

        if overview.tech_stack:
            lines.append("## Tech Stack\n")
            for t in overview.tech_stack:
                ver = f" {t.version}" if t.version else ""
                cat = f" ({t.category})" if t.category else ""
                lines.append(f"- **{t.name}**{ver}{cat}")
            lines.append("")

        if overview.key_features:
            lines.append("## Key Features\n")
            for feat in overview.key_features:
                lines.append(f"- {feat}")
            lines.append("")

        if overview.setup_instructions:
            lines.append("## Getting Started\n")
            for i, step in enumerate(overview.setup_instructions, 1):
                lines.append(f"{i}. {step}")
            lines.append("")

        return "\n".join(lines)

    def _build_architecture_page(self, arch) -> str:
        lines = ["# Architecture\n"]
        if arch.architecture_type:
            lines.append(f"**Type:** {arch.architecture_type}\n")
        if arch.description:
            lines.append(f"{arch.description}\n")

        if arch.mermaid_component:
            lines.append("## Component Diagram\n")
            lines.append(f"```mermaid\n{arch.mermaid_component}\n```\n")

        if arch.components:
            lines.append("## Components\n")
            for c in arch.components:
                lines.append(f"### {c.name}\n")
                if c.purpose:
                    lines.append(f"{c.purpose}\n")
                if c.files:
                    lines.append("Files: " + ", ".join(f"`{f}`" for f in c.files) + "\n")

        if arch.mermaid_sequence:
            lines.append("## Sequence Diagram\n")
            lines.append(f"```mermaid\n{arch.mermaid_sequence}\n```\n")

        if arch.call_graph:
            lines.append("## Call Graph\n")
            lines.append(
                "Deterministic view built from the Python AST: who calls whom, "
                "resolved within the project. Cross-file edges follow explicit "
                "imports; dynamic dispatch is out of scope.\n"
            )
            lines.append(f"```mermaid\n{arch.call_graph}\n```\n")

        if arch.data_flow_graph:
            lines.append("## Data Flow Graph\n")
            lines.append(
                "Deterministic view built from the Python AST: for each class "
                "defined in the project, which functions create it and which "
                "functions receive it. Only explicit annotations and direct "
                "constructor calls count; factories and duck typing are out of "
                "scope.\n"
            )
            lines.append(f"```mermaid\n{arch.data_flow_graph}\n```\n")

        if arch.data_flow:
            lines.append("## Data Flow\n")
            lines.append(f"{arch.data_flow}\n")

        return "\n".join(lines)

    def _collect_cards(self, wiki_data: WikiData, graph, root: str) -> list[ModuleCard]:
        # one compact card per module: what it is for, what it exposes, what
        # it touches, which file is the way in, and where the churn is; enough
        # to pick a starting point before opening the page
        modules = [m for m in wiki_data.modules if m.purpose or m.files]
        if not modules:
            return []
        churn, churn_commits = file_churn(root)
        entries = graph.get_entry_points()
        # a module caught in an import cycle gets a heads-up on its card; that
        # loop is exactly the trap a newcomer reads cards to avoid
        cycle_mods = {_get_module(f) for cycle in graph.find_circular_dependencies() for f in cycle}
        cards: list[ModuleCard] = []
        for mod in modules:
            symbols = [s.name for f in mod.files for s in f.key_symbols]
            mod_entries = [e for e in entries if _get_module(e) == mod.name]
            cards.append(
                ModuleCard(
                    name=mod.name,
                    purpose=mod.purpose,
                    file_count=len(mod.files),
                    key_symbols=symbols[:5],
                    extra_symbols=max(0, len(symbols) - 5),
                    key_concepts=[c.name for c in mod.key_concepts[:4]],
                    entry_files=mod_entries[:3],
                    extra_entries=max(0, len(mod_entries) - 3),
                    in_cycle=mod.name in cycle_mods,
                    hotspots=module_hotspots(churn, churn_commits, mod.name) or [],
                    relationships=[(r.source, r.target) for r in mod.relationships[:4]],
                    page_id=f"modules/{mod.name}",
                )
            )
        return cards

    def _build_cards_page(self, cards: list[ModuleCard]) -> str:
        lines = [
            "# Knowledge Cards\n",
            "One card per module: its purpose, its public surface, its",
            "internal links, and the file to open first. Pick a card, then",
            "open the full module page.\n",
        ]
        for card in cards:
            lines.append(f"### `{card.name}`\n")
            if card.purpose:
                lines.append(f"> {card.purpose}\n")
            if card.in_cycle:
                lines.append(
                    "Cycle: files here import each other in a loop, so read them "
                    f"as a set; see [Dependencies]({_rel_href('cards', 'dependencies')}).\n"
                )
            facts: list[str] = []
            if card.file_count:
                facts.append(f"{card.file_count} files")
            if card.key_symbols:
                more = f" +{card.extra_symbols} more" if card.extra_symbols else ""
                facts.append("symbols " + ", ".join(f"`{n}`" for n in card.key_symbols) + more)
            if card.key_concepts:
                facts.append("concepts " + ", ".join(card.key_concepts))
            if facts:
                lines.append(" · ".join(facts) + "\n")
            if card.entry_files:
                more = f" +{card.extra_entries} more" if card.extra_entries else ""
                lines.append(
                    "Entry: " + ", ".join(f"`{e}`" for e in card.entry_files) + more + "\n"
                )
            if card.hotspots:
                lines.append(
                    "Hot (most commits): "
                    + ", ".join(f"`{p}` ({n})" for p, n in card.hotspots)
                    + "\n"
                )
            if card.relationships:
                rels = ", ".join(
                    f"`{source}` → `{target}`" for source, target in card.relationships
                )
                lines.append(f"Internal links: {rels}\n")
            lines.append(f"[Open the full page]({_rel_href('cards', card.page_id)})\n")
        return "\n".join(lines)

    def _build_module_page(self, mod) -> str:
        lines = [f"# {mod.name}\n"]
        if mod.purpose:
            lines.append(f"> {mod.purpose}\n")
        if mod.description:
            lines.append(f"{mod.description}\n")

        if mod.files:
            lines.append("## Files\n")
            for f in mod.files:
                lines.append(f"### `{f.path}`\n")
                if f.purpose:
                    lines.append(f"{f.purpose}\n")
                if f.key_symbols:
                    for s in f.key_symbols:
                        desc = f" - {s.description}" if s.description else ""
                        lines.append(f"- `{s.name}` ({s.kind}){desc}")
                    lines.append("")

        if mod.key_concepts:
            lines.append("## Key Concepts\n")
            for c in mod.key_concepts:
                lines.append(f"- **{c.name}**: {c.explanation}")
            lines.append("")

        if mod.relationships:
            lines.append("## Internal Relationships\n")
            for r in mod.relationships:
                lines.append(f"- `{r.source}` → `{r.target}`: {r.description}")
            lines.append("")

        return "\n".join(lines)

    def _build_testmap_page(self, project: ProjectContext) -> str:
        # which test files import which source files, and which files no test
        # reaches; an orientation aid, not a coverage report — dynamic loading
        # is not chased, so "untested" means "nothing imports it from a test"
        from .testmap import build_test_map

        m = build_test_map(project)
        if m.test_file_count == 0:
            return ""
        lines = [
            "# Test Map\n",
            f"{m.test_file_count} test files reach {m.reached_source_count} of "
            f"{m.reached_source_count + len(m.untested_sources)} source files. "
            "Reach means a test imports the file; dynamic loading is not chased, "
            "so this is where to look, not a coverage claim.\n",
        ]
        rows = sorted(m.by_source.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        if rows:
            lines.append("## Source files, by tests that reach them\n")
            lines.append("| Source | Tests | Symbols imported |")
            lines.append("| --- | --- | --- |")
            for src, refs in rows:
                tests = ", ".join(f"`{r.test}`" for r in refs)
                symbols = sorted({s for r in refs for s in r.symbols})
                sym = ", ".join(f"`{s}`" for s in symbols[:6])
                if len(symbols) > 6:
                    sym += f" +{len(symbols) - 6} more"
                lines.append(f"| `{src}` | {tests} | {sym or '—'} |")
            lines.append("")
        if m.untested_sources:
            lines.append("## Sources no test file imports\n")
            shown = m.untested_sources[:40]
            more = len(m.untested_sources) - len(shown)
            lines.append(
                ", ".join(f"`{p}`" for p in shown) + (f" (+{more} more)" if more else "") + "\n"
            )
        if m.unreferencing_tests:
            lines.append("## Test files that reach no source file\n")
            lines.append(
                "Fixture helpers or fully mocked tests; open them before trusting their names.\n"
            )
            shown = m.unreferencing_tests[:40]
            more = len(m.unreferencing_tests) - len(shown)
            lines.append(
                ", ".join(f"`{p}`" for p in shown) + (f" (+{more} more)" if more else "") + "\n"
            )
        return "\n".join(lines)

    def _collect_symbols(self, wiki_data: WikiData) -> list[SymbolEntry]:
        # Keep first-appearance kind order and first description, then sort
        # modules and names exactly as the Markdown index has always done.
        kinds: dict[str, dict[str, dict[str, SymbolEntry]]] = {}
        for mod in wiki_data.modules:
            for f in mod.files:
                for s in f.key_symbols:
                    bucket = kinds.setdefault(s.kind or "other", {}).setdefault(mod.name, {})
                    if s.name not in bucket:
                        bucket[s.name] = SymbolEntry(
                            name=s.name,
                            kind=s.kind or "other",
                            description=s.description,
                            module=mod.name,
                            page_id=f"modules/{mod.name}",
                        )
        entries: list[SymbolEntry] = []
        for modules in kinds.values():
            for mod_name in sorted(modules):
                for name in sorted(modules[mod_name]):
                    entries.append(modules[mod_name][name])
        return entries

    def _build_symbol_index_page(self, symbols: list[SymbolEntry]) -> str:
        if not symbols:
            return ""

        module_count = len({symbol.module for symbol in symbols})
        lines = ["# Symbol Index\n"]
        lines.append(f"{len(symbols)} symbols across {module_count} modules.\n")
        for kind, kind_entries in groupby(symbols, key=lambda symbol: symbol.kind):
            lines.append(f"## {kind.capitalize()}\n")
            for mod_name, module_entries in groupby(kind_entries, key=lambda symbol: symbol.module):
                href = _rel_href("symbols", f"modules/{mod_name}")
                lines.append(f"### [{mod_name}]({href})\n")
                for symbol in module_entries:
                    suffix = f" - {symbol.description}" if symbol.description else ""
                    lines.append(f"- [`{symbol.name}`]({href}){suffix}")
                lines.append("")
        return "\n".join(lines)

    def _build_reading_guide_page(self, guide) -> str:
        lines = ["# Reading Guide\n"]
        if guide.introduction:
            lines.append(f"{guide.introduction}\n")

        for step in guide.steps:
            time_est = f" (~{step.time_estimate})" if step.time_estimate else ""
            lines.append(f"## Step {step.order}: {step.title}{time_est}\n")
            if step.files:
                lines.append("**Files:** " + ", ".join(f"`{f}`" for f in step.files) + "\n")
            if step.explanation:
                lines.append(f"{step.explanation}\n")

        if guide.tips:
            lines.append("## Tips\n")
            for tip in guide.tips:
                lines.append(f"- {tip}")
            lines.append("")

        return "\n".join(lines)

    def _build_dependency_page(self, graph: DependencyGraph, mermaid: str) -> str:
        lines = ["# Module Dependencies\n"]
        lines.append("```mermaid\n" + mermaid + "\n```\n")

        # core files
        core = graph.get_core_files(10)
        if core:
            lines.append("## Core Files (by PageRank)\n")
            for i, path in enumerate(core, 1):
                lines.append(f"{i}. `{path}`")
            lines.append("")

        # entry points
        entries = graph.get_entry_points()
        if entries:
            lines.append("## Likely Entry Points\n")
            for e in entries[:10]:
                lines.append(f"- `{e}`")
            lines.append("")

        # circular dependencies (an architectural smell worth surfacing)
        cycles = graph.find_circular_dependencies()
        if cycles:
            lines.append("## Circular Dependencies\n")
            lines.append(
                "These groups of files import each other in a cycle, so you can't "
                "fully understand one without the others; consider breaking the loop "
                "to reduce coupling.\n"
            )
            for cycle in cycles:
                files = ", ".join(f"`{p}`" for p in cycle)
                lines.append(f"- {files}")
            lines.append("")

        # isolated files (likely dead code worth surfacing)
        isolated = graph.find_isolated_files()
        if isolated:
            lines.append("## Isolated Files\n")
            lines.append(
                "These files import nothing in the project and are imported by "
                "nothing -- likely dead code, stray scripts, or modules that were "
                "never wired in.\n"
            )
            for f in isolated[:15]:
                lines.append(f"- `{f}`")
            lines.append("")

        return "\n".join(lines)


# single-backtick spans, but not when they are already the text of a markdown link
_CODE_SPAN = re.compile(r"(?<!\[)`([^`\n]+)`(?!\]\()")


def _apply_cross_links(
    content: str,
    page_id: str,
    symbols: dict[str, str],
    files: dict[str, str],
) -> str:
    out: list[str] = []
    in_fence = False
    for line in content.split("\n"):
        if line.startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        out.append(_linkify_line(line, page_id, symbols, files))
    return "\n".join(out)


def _linkify_line(
    line: str,
    page_id: str,
    symbols: dict[str, str],
    files: dict[str, str],
) -> str:
    def sub(m: re.Match) -> str:
        name = m.group(1)
        target = files.get(name) or symbols.get(name)
        # a page never links to itself
        if target is None or target == page_id:
            return m.group(0)
        return f"[`{name}`]({_rel_href(page_id, target)})"

    return _CODE_SPAN.sub(sub, line)


def _rel_href(from_page_id: str, to_page_id: str) -> str:
    base = posixpath.dirname(from_page_id)
    target = f"{to_page_id}.md"
    return target if not base else posixpath.relpath(target, base)
