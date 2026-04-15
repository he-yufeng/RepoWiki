"""data models for repowiki analysis pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """metadata about a single file in the project."""

    path: str
    size: int
    language: str = "unknown"
    lines: int = 0
    preview: str = ""
    content: str = ""
    is_config: bool = False
    is_entrypoint: bool = False


class ProjectContext(BaseModel):
    """everything we know about a project before LLM analysis."""

    name: str
    root: str
    files: list[FileInfo] = Field(default_factory=list)
    file_tree: str = ""

    @property
    def total_lines(self) -> int:
        return sum(f.lines for f in self.files)


# --- LLM analysis output models ---


class TechItem(BaseModel):
    name: str
    category: str = ""  # language, framework, database, etc.
    version: str = ""


class ProjectOverview(BaseModel):
    name: str = ""
    one_liner: str = ""
    description: str = ""
    tech_stack: list[TechItem] = Field(default_factory=list)
    setup_instructions: list[str] = Field(default_factory=list)
    key_features: list[str] = Field(default_factory=list)


class Symbol(BaseModel):
    name: str
    kind: str = ""  # function, class, variable, constant
    line: int = 0
    description: str = ""


class FileDoc(BaseModel):
    path: str
    purpose: str = ""
    key_symbols: list[Symbol] = Field(default_factory=list)


class Relationship(BaseModel):
    source: str
    target: str
    description: str = ""


class Concept(BaseModel):
    name: str
    explanation: str = ""


class ModuleDoc(BaseModel):
    name: str
    purpose: str = ""
    description: str = ""
    files: list[FileDoc] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    key_concepts: list[Concept] = Field(default_factory=list)


class Component(BaseModel):
    name: str
    purpose: str = ""
    files: list[str] = Field(default_factory=list)


class ArchitectureDiagram(BaseModel):
    architecture_type: str = ""  # monolith, client-server, microservices, etc.
    description: str = ""
    components: list[Component] = Field(default_factory=list)
    mermaid_component: str = ""
    mermaid_sequence: str = ""
    data_flow: str = ""


class ReadingStep(BaseModel):
    order: int
    title: str
    files: list[str] = Field(default_factory=list)
    explanation: str = ""
    time_estimate: str = ""


class ReadingGuide(BaseModel):
    introduction: str = ""
    steps: list[ReadingStep] = Field(default_factory=list)
    tips: list[str] = Field(default_factory=list)


class WikiData(BaseModel):
    """complete wiki analysis output."""

    overview: ProjectOverview = Field(default_factory=ProjectOverview)
    modules: list[ModuleDoc] = Field(default_factory=list)
    architecture: ArchitectureDiagram = Field(default_factory=ArchitectureDiagram)
    reading_guide: ReadingGuide = Field(default_factory=ReadingGuide)
    file_index: dict[str, FileDoc] = Field(default_factory=dict)
