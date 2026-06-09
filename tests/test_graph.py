from repowiki.core.graph import DependencyGraph
from repowiki.core.models import FileInfo, ProjectContext


def _project(files: dict[str, tuple[str, str]]) -> ProjectContext:
    return ProjectContext(
        name="fixture",
        root=".",
        files=[
            FileInfo(path=path, size=len(content), language=language, content=content)
            for path, (language, content) in files.items()
        ],
    )


def test_python_relative_imports_resolve_inside_src_package():
    project = _project(
        {
            "src/app/api/routes.py": ("python", "from ..services.users import get_user\n"),
            "src/app/services/users.py": ("python", "def get_user(): ...\n"),
        }
    )

    graph = DependencyGraph.build_from_project(project).graph

    assert ("src/app/api/routes.py", "src/app/services/users.py") in graph.edges


def test_javascript_relative_import_normalizes_parent_segments():
    project = _project(
        {
            "frontend/src/pages/home.tsx": (
                "typescript",
                "import { api } from '../lib/api';\n",
            ),
            "frontend/src/lib/api.ts": ("typescript", "export const api = {};\n"),
        }
    )

    graph = DependencyGraph.build_from_project(project).graph

    assert ("frontend/src/pages/home.tsx", "frontend/src/lib/api.ts") in graph.edges


def test_javascript_relative_import_resolves_index_module():
    project = _project(
        {
            "frontend/src/app.ts": ("typescript", "import { store } from './store';\n"),
            "frontend/src/store/index.ts": ("typescript", "export const store = {};\n"),
        }
    )

    graph = DependencyGraph.build_from_project(project).graph

    assert ("frontend/src/app.ts", "frontend/src/store/index.ts") in graph.edges
