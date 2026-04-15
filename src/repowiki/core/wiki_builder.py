"""assemble wiki pages from analysis results."""

from __future__ import annotations

from dataclasses import dataclass, field

from repowiki.core.graph import DependencyGraph
from repowiki.core.models import ProjectContext, WikiData


@dataclass
class WikiPage:
    id: str
    title: str
    content: str
    parent_id: str = ""
    order: int = 0


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
            pages.append(WikiPage(id="architecture", title="Architecture", content=arch_md, order=1))
            sidebar.append(SidebarItem(title="Architecture", page_id="architecture"))

        # 3. module pages
        module_sidebar = SidebarItem(title="Modules", page_id="", children=[])
        for i, mod in enumerate(wiki_data.modules):
            mod_id = f"modules/{mod.name}"
            mod_md = self._build_module_page(mod)
            pages.append(WikiPage(
                id=mod_id, title=mod.name, content=mod_md,
                parent_id="modules", order=i,
            ))
            module_sidebar.children.append(SidebarItem(title=mod.name, page_id=mod_id))
        if module_sidebar.children:
            sidebar.append(module_sidebar)

        # 4. reading guide
        guide = wiki_data.reading_guide
        if guide.steps:
            guide_md = self._build_reading_guide_page(guide)
            pages.append(WikiPage(id="reading-guide", title="Reading Guide", content=guide_md, order=10))
            sidebar.append(SidebarItem(title="Reading Guide", page_id="reading-guide"))

        # 5. dependency graph
        mermaid = graph.to_mermaid()
        if mermaid:
            dep_md = self._build_dependency_page(graph, mermaid)
            pages.append(WikiPage(id="dependencies", title="Dependencies", content=dep_md, order=11))
            sidebar.append(SidebarItem(title="Dependencies", page_id="dependencies"))

        return Wiki(pages=pages, sidebar=sidebar, project_name=project.name)

    def _build_overview_page(self, overview, project) -> str:
        lines = [f"# {overview.name or project.name}\n"]
        if overview.one_liner:
            lines.append(f"> {overview.one_liner}\n")
        if overview.description:
            lines.append(f"{overview.description}\n")

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

        if arch.data_flow:
            lines.append("## Data Flow\n")
            lines.append(f"{arch.data_flow}\n")

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

        return "\n".join(lines)
