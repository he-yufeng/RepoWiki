# repowiki

> Generates wiki documentation for codebases using LLMs.

A tool that analyzes local or remote code repositories, constructs dependency graphs, uses LLMs to generate structured documentation (overviews, module summaries, architecture diagrams, reading guides), and exports the results as HTML, Markdown, JSON, or a web server. Supports CLI and web interfaces, caching, incremental updates, and Q&A chat.

## Files

### `src/repowiki/config.py`

Manages configuration settings, aliases, and environment overrides.

- `Config` (class) - Dataclass holding user-configurable settings like model, API key, language, and file limits.
- `resolve_model` (function) - Resolves shorthand model aliases to full provider/model strings.
- `MODEL_ALIASES` (variable) - Dictionary mapping common model shortcuts to full identifiers.
- `MODEL_API_BASES` (variable) - Maps specific model strings to their API base URLs for OpenAI-compatible vendors.

### `src/repowiki/__main__.py`

Entry point for running the module as a CLI via python -m.

- `cli` (function) - Invokes the main CLI function from repowiki.cli.

### `src/repowiki/server/app.py`

FastAPI application factory for the web interface.

- `create_app` (function) - Creates and configures the FastAPI app instance.
- `get_cache` (function) - Retrieves the cache instance for the app.
- `get_projects` (function) - Returns the in-memory project store.

### `src/repowiki/__init__.py`

Module initialization and version definition.

- `__version__` (variable) - Current version of the repowiki package.

### `src/repowiki/cli.py`

Command-line interface for all repowiki operations.

- `cli` (function) - Main CLI entry point with command groups.
- `scan` (function) - Scans a directory or URL and generates wiki documentation.
- `serve` (function) - Starts the web server for interactive wiki browsing.
- `chat` (function) - Interactive Q&A about a codebase in the terminal.
- `repo_map` (function) - Prints a dependency-ranked file list.
- `diff_map` (function) - Generates a review order for changed files in a git diff.
- `cache_clear` (function) - Clears cached LLM results.
- `config_group` (function) - Manages configuration settings via subcommands.

### `src/repowiki/core/analyzer.py`

Orchestrates the multi-step LLM analysis pipeline.

- `Analyzer` (class) - Runs the full wiki generation process: overview, module analysis, architecture, reading guide.

### `src/repowiki/core/cache.py`

SQLite-based cache for LLM analysis results and project data.

- `Cache` (class) - Async cache manager with TTL support for storing and retrieving JSON data.
- `content_hash` (function) - Generates a truncated SHA256 hash for cache keys.

### `src/repowiki/core/diff.py`

Analyzes git diffs to rank changed files by importance for review.

- `DiffReport` (class) - Container for changed files and their review metrics.
- `build_diff_report` (function) - Ranks diff files using PageRank and dependency counts.
- `diff_files` (function) - Parses git diff output into status-path tuples.

### `src/repowiki/core/graph.py`

Builds dependency graphs and computes PageRank for file importance.

- `DependencyGraph` (class) - Constructs and analyzes file dependency graphs, ranks files, detects cycles.
- `_pagerank_power_iteration` (function) - Computes PageRank scores via power iteration.

### `src/repowiki/core/models.py`

Pydantic models for data structures in the analysis pipeline.

- `FileInfo` (class) - Metadata and content preview for a single file.
- `ProjectContext` (class) - Complete project metadata before LLM analysis.
- `WikiData` (class) - Final output of the analysis pipeline, containing all generated documentation.

### `src/repowiki/core/rag.py`

Lightweight TF-IDF retrieval for Q&A chat and module indexing.

- `SimpleRAG` (class) - TF-IDF based code retriever with incremental indexing.
- `ModuleIndex` (class) - Indexes module documentation for natural language query matching.
- `load_or_build_index` (function) - Loads or rebuilds the RAG index based on file changes.

### `src/repowiki/core/scanner.py`

Scans project directories, collects file metadata, and applies ignore rules.

- `scan_directory` (function) - Walks a directory, reads files within limits, and returns FileInfo list.
- `IgnoreRules` (class) - Applies .gitignore-like patterns to skip files/directories.

### `src/repowiki/core/skeleton.py`

Generates symbol skeletons for oversized Python files instead of truncating.

- `python_skeleton` (function) - Extracts module docstring and top-level class/function signatures.
- `context_for_file` (function) - Returns file content within token budget, using skeletons for large Python files.

### `src/repowiki/core/state.py`

Manages per-output-directory state for incremental wiki regeneration.

- `load_state` (function) - Reads the state file to determine if incremental build is possible.
- `save_state` (function) - Saves the current state to enable future incremental builds.

### `src/repowiki/core/wiki_builder.py`

Assembles wiki pages from analysis results and handles cross-linking.

- `WikiBuilder` (class) - Constructs the wiki structure from analyzed data.
- `Wiki` (class) - Holds the complete wiki with pages and sidebar.

### `src/repowiki/export/html.py`

Exports the wiki as a self-contained HTML file.

- `export_html` (function) - Generates a single HTML file with sidebar navigation.
- `_markdown_to_html` (function) - Converts Markdown to HTML without external dependencies.

### `src/repowiki/export/json_export.py`

Exports the wiki as a JSON file.

- `export_json` (function) - Writes the full wiki structure to JSON, avoiding redundant writes.

### `src/repowiki/export/markdown.py`

Exports the wiki as a directory of Markdown files.

- `export_markdown` (function) - Writes each wiki page as a .md file and generates a sidebar.

### `src/repowiki/export/site.py`

Adds docsify loader for GitHub Pages to markdown exports.

- `write_site_loader` (function) - Writes index.html and .nojekyll to make markdown exports servable.

### `src/repowiki/ingest/github.py`

Clones remote git repositories and ingests them into ProjectContext.

- `ingest_github` (function) - Shallow-clones a git repo and returns a ProjectContext.
- `parse_git_url` (function) - Extracts host, owner, and repo from a URL.

### `src/repowiki/ingest/local.py`

Ingests a local directory into a ProjectContext.

- `ingest_local` (function) - Scans a local directory and packages it into a ProjectContext.
- `_guess_project_name` (function) - Attempts to extract the project name from config files.

### `src/repowiki/llm/client.py`

Async LLM client wrapper using litellm.

- `LLMClient` (class) - Handles completions and streaming with retries and error handling.

### `src/repowiki/llm/prompts.py`

Prompt templates for all LLM analysis steps and chat.

- `build_overview_prompt` (function) - Constructs the prompt for generating project overview.
- `build_module_prompt` (function) - Constructs the prompt for module documentation.
- `build_chat_prompt` (function) - Constructs the prompt for Q&A chat.
- `extract_json` (function) - Extracts JSON from LLM output, handling markdown fences.

### `src/repowiki/server/models.py`

Pydantic models for web API requests and responses.

- `ScanRequest` (class) - Request model for starting a scan.
- `ChatRequest` (class) - Request model for chat queries with history.

### `src/repowiki/server/routers/chat.py`

Q&A chat endpoint with RAG retrieval and streaming.

- `chat` (function) - SSE streaming endpoint for chat with context retrieval.

### `src/repowiki/server/routers/scan.py`

Scan and project management endpoints.

- `start_scan` (function) - Initiates a background scan task.
- `stream_status` (function) - SSE endpoint for scan progress updates.

### `src/repowiki/server/routers/wiki.py`

Wiki content and file access endpoints.

- `get_wiki` (function) - Returns the full wiki structure.
- `get_page` (function) - Returns content for a specific wiki page.
- `get_graph` (function) - Returns dependency graph data and Mermaid diagram.

## Key Concepts

- **Dependency Graph**: A directed graph of file imports, used to compute PageRank scores for file importance and detect cycles.
- **LLM Analysis Pipeline**: Multi-step process where LLMs generate overviews, module docs, architecture diagrams, and reading guides based on code context.
- **Caching**: SQLite cache stores LLM results and project data to avoid redundant API calls and enable incremental builds.
- **RAG (Retrieval-Augmented Generation)**: TF-IDF based retrieval of code chunks for Q&A chat, enhanced by module card indexing for better query matching.
- **Incremental Regeneration**: Uses state files and content hashing to rebuild only changed parts of the wiki on subsequent runs.
- **Symbol Skeletons**: For oversized Python files, extracts signatures and docstrings instead of truncating, providing better context to LLMs.

## Internal Relationships

- `src/repowiki/cli.py` → `src/repowiki/config.py`: Uses Config.load() for CLI command configuration.
- `src/repowiki/cli.py` → `src/repowiki/core/analyzer.py`: Calls Analyzer for the main analysis pipeline.
- `src/repowiki/core/analyzer.py` → `src/repowiki/llm/client.py`: Uses LLMClient to make LLM requests.
- `src/repowiki/core/analyzer.py` → `src/repowiki/llm/prompts.py`: Uses prompt-building functions for each analysis step.
- `src/repowiki/core/analyzer.py` → `src/repowiki/core/cache.py`: Caches LLM results to avoid redundant calls.
- `src/repowiki/core/analyzer.py` → `src/repowiki/core/graph.py`: Uses DependencyGraph for file ranking and structure.
- `src/repowiki/core/analyzer.py` → `src/repowiki/core/models.py`: Uses ProjectContext and WikiData models for data flow.
- `src/repowiki/core/rag.py` → `src/repowiki/core/scanner.py`: Uses FileInfo from scanning to build the index.
- `src/repowiki/server/routers/chat.py` → `src/repowiki/core/rag.py`: Uses SimpleRAG for retrieval in chat endpoints.
- `src/repowiki/server/routers/scan.py` → `src/repowiki/ingest/github.py`: Calls ingest_github for remote repo scanning.
- `src/repowiki/server/routers/scan.py` → `src/repowiki/ingest/local.py`: Calls ingest_local for local directory scanning.
- `src/repowiki/export/markdown.py` → `src/repowiki/core/wiki_builder.py`: Uses Wiki model to generate Markdown output.
