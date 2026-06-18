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


def test_find_circular_dependencies_detects_mutual_imports():
    project = _project(
        {
            "src/app/api/routes.py": ("python", "from ..services.users import get_user\n"),
            "src/app/services/users.py": ("python", "from ..api.routes import handler\n"),
            "src/app/util.py": ("python", "VALUE = 1\n"),
        }
    )

    cycles = DependencyGraph.build_from_project(project).find_circular_dependencies()

    assert len(cycles) == 1
    assert cycles[0] == ["src/app/api/routes.py", "src/app/services/users.py"]
    # the standalone file is not part of any cycle
    assert "src/app/util.py" not in {f for c in cycles for f in c}


def test_find_circular_dependencies_empty_for_acyclic_graph():
    project = _project(
        {
            "src/app/api/routes.py": ("python", "from ..services.users import get_user\n"),
            "src/app/services/users.py": ("python", "def get_user(): ...\n"),
        }
    )

    assert DependencyGraph.build_from_project(project).find_circular_dependencies() == []


def test_find_isolated_files_flags_disconnected_modules():
    project = _project(
        {
            "src/app/api/routes.py": ("python", "from ..services.users import get_user\n"),
            "src/app/services/users.py": ("python", "def get_user(): ...\n"),
            "src/app/scratch.py": ("python", "VALUE = 1\n"),
        }
    )

    graph = DependencyGraph.build_from_project(project)

    # scratch.py has no edges either way; it is the only isolated file.
    assert graph.find_isolated_files() == ["src/app/scratch.py"]
    # and an isolated file must not masquerade as an entry point
    assert "src/app/scratch.py" not in graph.get_entry_points()


def test_entry_points_require_outgoing_imports():
    project = _project(
        {
            "src/app/api/routes.py": ("python", "from ..services.users import get_user\n"),
            "src/app/services/users.py": ("python", "def get_user(): ...\n"),
        }
    )

    entries = DependencyGraph.build_from_project(project).get_entry_points()

    # routes imports users, so it is a real entry point
    assert "src/app/api/routes.py" in entries
    # users imports nothing in the project: a leaf utility, not an entry point
    assert "src/app/services/users.py" not in entries
