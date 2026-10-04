# Symbol Index

165 symbols across 6 modules.

## Class

### [evals](modules/evals.md)

- [`EvalReport`](modules/evals.md) - Stores and calculates evaluation results including overall and per-repository scores

### [repowiki](modules/repowiki.md)

- [`Analyzer`](modules/repowiki.md) - Runs the full wiki generation process: overview, module analysis, architecture, reading guide.
- [`Cache`](modules/repowiki.md) - Async cache manager with TTL support for storing and retrieving JSON data.
- [`ChatRequest`](modules/repowiki.md) - Request model for chat queries with history.
- [`Config`](modules/repowiki.md) - Dataclass holding user-configurable settings like model, API key, language, and file limits.
- [`DependencyGraph`](modules/repowiki.md) - Constructs and analyzes file dependency graphs, ranks files, detects cycles.
- [`DiffReport`](modules/repowiki.md) - Container for changed files and their review metrics.
- [`FileInfo`](modules/repowiki.md) - Metadata and content preview for a single file.
- [`IgnoreRules`](modules/repowiki.md) - Applies .gitignore-like patterns to skip files/directories.
- [`LLMClient`](modules/repowiki.md) - Handles completions and streaming with retries and error handling.
- [`ModuleIndex`](modules/repowiki.md) - Indexes module documentation for natural language query matching.
- [`ProjectContext`](modules/repowiki.md) - Complete project metadata before LLM analysis.
- [`ScanRequest`](modules/repowiki.md) - Request model for starting a scan.
- [`SimpleRAG`](modules/repowiki.md) - TF-IDF based code retriever with incremental indexing.
- [`Wiki`](modules/repowiki.md) - Holds the complete wiki with pages and sidebar.
- [`WikiBuilder`](modules/repowiki.md) - Constructs the wiki structure from analyzed data.
- [`WikiData`](modules/repowiki.md) - Final output of the analysis pipeline, containing all generated documentation.

## Function

### [evals](modules/evals.md)

- [`run_eval`](modules/evals.md) - Executes the evaluation by matching questions to expected files and calculating accuracy metrics

### [frontend](modules/frontend.md)

- [`createRoot`](modules/frontend.md) - Creates a React root and renders the App component inside StrictMode.
- [`defineConfig`](modules/frontend.md) - Defines Vite configuration with React plugin, Tailwind CSS plugin, and server proxy to backend API.
- [`getFileContent`](modules/frontend.md) - Fetches the content and metadata of a source file from the project.
- [`getHeaders`](modules/frontend.md) - Returns HTTP headers including the API key from localStorage for authenticated requests.
- [`getPage`](modules/frontend.md) - Fetches the content of a specific wiki page by ID.
- [`getWiki`](modules/frontend.md) - Fetches the wiki structure (sidebar and pages) for a project.
- [`handleScan`](modules/frontend.md) - Handles form submission to start scanning a codebase, updates progress, and navigates to wiki view on completion.
- [`markdownToHtml`](modules/frontend.md) - Converts markdown text to HTML with support for code blocks, headings, blockquotes, bold, inline code, links, and lists.
- [`mermaid.initialize`](modules/frontend.md) - Initializes Mermaid with configuration to not start rendering automatically.
- [`mermaid.render`](modules/frontend.md) - Asynchronously renders Mermaid code to SVG.
- [`parseHash`](modules/frontend.md) - Parses URL hash (e.g., #L10-L20) to extract line range for highlighting.
- [`scanProject`](modules/frontend.md) - Initiates a codebase scan by sending a POST request to /api/scan with project details.
- [`splitMermaid`](modules/frontend.md) - Splits markdown content into an array of text and Mermaid code blocks using regex.
- [`streamChat`](modules/frontend.md) - Streams chat responses from the backend using Server-Sent Events (SSE).
- [`streamScanProgress`](modules/frontend.md) - Sets up an EventSource to stream scan progress updates from the backend.

### [repowiki](modules/repowiki.md)

- [`_guess_project_name`](modules/repowiki.md) - Attempts to extract the project name from config files.
- [`_markdown_to_html`](modules/repowiki.md) - Converts Markdown to HTML without external dependencies.
- [`_pagerank_power_iteration`](modules/repowiki.md) - Computes PageRank scores via power iteration.
- [`build_chat_prompt`](modules/repowiki.md) - Constructs the prompt for Q&A chat.
- [`build_diff_report`](modules/repowiki.md) - Ranks diff files using PageRank and dependency counts.
- [`build_module_prompt`](modules/repowiki.md) - Constructs the prompt for module documentation.
- [`build_overview_prompt`](modules/repowiki.md) - Constructs the prompt for generating project overview.
- [`cache_clear`](modules/repowiki.md) - Clears cached LLM results.
- [`chat`](modules/repowiki.md) - Interactive Q&A about a codebase in the terminal.
- [`cli`](modules/repowiki.md) - Invokes the main CLI function from repowiki.cli.
- [`config_group`](modules/repowiki.md) - Manages configuration settings via subcommands.
- [`content_hash`](modules/repowiki.md) - Generates a truncated SHA256 hash for cache keys.
- [`context_for_file`](modules/repowiki.md) - Returns file content within token budget, using skeletons for large Python files.
- [`create_app`](modules/repowiki.md) - Creates and configures the FastAPI app instance.
- [`diff_files`](modules/repowiki.md) - Parses git diff output into status-path tuples.
- [`diff_map`](modules/repowiki.md) - Generates a review order for changed files in a git diff.
- [`export_html`](modules/repowiki.md) - Generates a single HTML file with sidebar navigation.
- [`export_json`](modules/repowiki.md) - Writes the full wiki structure to JSON, avoiding redundant writes.
- [`export_markdown`](modules/repowiki.md) - Writes each wiki page as a .md file and generates a sidebar.
- [`extract_json`](modules/repowiki.md) - Extracts JSON from LLM output, handling markdown fences.
- [`get_cache`](modules/repowiki.md) - Retrieves the cache instance for the app.
- [`get_graph`](modules/repowiki.md) - Returns dependency graph data and Mermaid diagram.
- [`get_page`](modules/repowiki.md) - Returns content for a specific wiki page.
- [`get_projects`](modules/repowiki.md) - Returns the in-memory project store.
- [`get_wiki`](modules/repowiki.md) - Returns the full wiki structure.
- [`ingest_github`](modules/repowiki.md) - Shallow-clones a git repo and returns a ProjectContext.
- [`ingest_local`](modules/repowiki.md) - Scans a local directory and packages it into a ProjectContext.
- [`load_or_build_index`](modules/repowiki.md) - Loads or rebuilds the RAG index based on file changes.
- [`load_state`](modules/repowiki.md) - Reads the state file to determine if incremental build is possible.
- [`parse_git_url`](modules/repowiki.md) - Extracts host, owner, and repo from a URL.
- [`python_skeleton`](modules/repowiki.md) - Extracts module docstring and top-level class/function signatures.
- [`repo_map`](modules/repowiki.md) - Prints a dependency-ranked file list.
- [`resolve_model`](modules/repowiki.md) - Resolves shorthand model aliases to full provider/model strings.
- [`save_state`](modules/repowiki.md) - Saves the current state to enable future incremental builds.
- [`scan`](modules/repowiki.md) - Scans a directory or URL and generates wiki documentation.
- [`scan_directory`](modules/repowiki.md) - Walks a directory, reads files within limits, and returns FileInfo list.
- [`serve`](modules/repowiki.md) - Starts the web server for interactive wiki browsing.
- [`start_scan`](modules/repowiki.md) - Initiates a background scan task.
- [`stream_status`](modules/repowiki.md) - SSE endpoint for scan progress updates.
- [`write_site_loader`](modules/repowiki.md) - Writes index.html and .nojekyll to make markdown exports servable.

### [tests](modules/tests.md)

- [`test_analyzer_passes_configured_max_tokens`](modules/tests.md) - Tests analyzer respects token limits
- [`test_card_shows_the_entry_file_from_the_dependency_graph`](modules/tests.md) - Tests entry file display in cards
- [`test_cards_page_lists_one_card_per_module`](modules/tests.md) - Tests card generation per module
- [`test_chat_prompt_without_history_stays_two_messages`](modules/tests.md) - Tests basic prompt structure
- [`test_chat_router_threads_history_into_prompt`](modules/tests.md) - Tests chat endpoint with conversation history
- [`test_client_side_route_falls_back_to_app_shell`](modules/tests.md) - Tests SPA fallback routing
- [`test_content_change_invalidates_the_saved_index`](modules/tests.md) - Tests index invalidation
- [`test_context_for_file_prefers_skeleton_for_big_python`](modules/tests.md) - Tests skeleton preference over truncation
- [`test_diff_files_parses_modified_added_deleted`](modules/tests.md) - Tests diff file parsing
- [`test_entries_link_to_owning_module_and_keep_descriptions`](modules/tests.md) - Tests symbol linking and descriptions
- [`test_entry_points_require_outgoing_imports`](modules/tests.md) - Tests entry point identification
- [`test_find_circular_dependencies_detects_mutual_imports`](modules/tests.md) - Tests circular dependency detection
- [`test_first_run_writes_all_pages_and_state`](modules/tests.md) - Tests initial full generation
- [`test_fixture_suite_holds_baseline`](modules/tests.md) - Tests RAG performance against baseline
- [`test_fresh_entry_survives_default_ttl`](modules/tests.md) - Tests cache entry persistence
- [`test_history_threads_before_the_question_in_order`](modules/tests.md) - Tests history integration in prompts
- [`test_html_export_skips_the_write_when_content_is_unchanged`](modules/tests.md) - Tests incremental HTML export
- [`test_html_export_turns_page_links_into_show_page_calls`](modules/tests.md) - Tests HTML link conversion
- [`test_html_export_writes_a_file_with_the_project_title`](modules/tests.md) - Tests basic HTML export
- [`test_index_round_trip`](modules/tests.md) - Tests index serialization
- [`test_kind_sections_follow_first_appearance_order`](modules/tests.md) - Tests symbol grouping by kind
- [`test_known_symbol_mention_becomes_a_link`](modules/tests.md) - Tests symbol mention linking
- [`test_llm_client_construction_imports_litellm`](modules/tests.md) - Tests on-demand LLM import
- [`test_map_json_ranks_by_dependency_pagerank`](modules/tests.md) - Tests JSON map output with PageRank
- [`test_map_text_lists_files_and_top_limit`](modules/tests.md) - Tests text map output
- [`test_mimo_alias_resolves`](modules/tests.md) - Tests model alias resolution
- [`test_module_analysis_reuses_cache_on_second_run`](modules/tests.md) - Verifies cache reuse for module analysis
- [`test_module_boost_surfaces_zero_overlap_file`](modules/tests.md) - Tests module-based boosting
- [`test_non_transient_error_is_not_retried`](modules/tests.md) - Tests no retry on fatal errors
- [`test_overview_page_flags_partial_coverage`](modules/tests.md) - Tests coverage warnings in overview
- [`test_package_cli_and_analyzer_imports_stay_litellm_free`](modules/tests.md) - Tests lazy import avoidance
- [`test_package_imports`](modules/tests.md) - Tests basic package import
- [`test_reading_guide_ranks_by_pagerank_not_scan_order`](modules/tests.md) - Verifies reading guide uses PageRank for file ordering
- [`test_report_counts_oversized_files_with_example_paths`](modules/tests.md) - Tests oversized file reporting
- [`test_report_ranks_changed_files_by_pagerank_and_blast_radius`](modules/tests.md) - Tests ranking of changed files
- [`test_retrieve_ranks_relevant_file_first`](modules/tests.md) - Tests retrieval ranking
- [`test_root_serves_built_frontend`](modules/tests.md) - Tests frontend serving
- [`test_scan_registers_project_and_background_task_runs`](modules/tests.md) - Tests project registration
- [`test_scan_respects_gitignore_and_repowikiignore`](modules/tests.md) - Tests ignore file handling
- [`test_scan_skips_minified_suffixes`](modules/tests.md) - Tests minified file filtering
- [`test_serve_passes_the_target_through`](modules/tests.md) - Tests serve command target passing
- [`test_single_file_change_regenerates_only_its_module_page`](modules/tests.md) - Tests targeted regeneration
- [`test_skeleton_extracts_module_doc_classes_and_functions`](modules/tests.md) - Tests Python skeleton extraction
- [`test_token_never_leaks_into_errors`](modules/tests.md) - Tests token security in error messages
- [`test_token_used_for_github_clone`](modules/tests.md) - Tests token authentication for GitHub
- [`test_transient_error_retries_until_success`](modules/tests.md) - Tests retry on transient errors
- [`test_vendor_aliases_get_endpoints`](modules/tests.md) - Tests vendor-specific API endpoints
- [`test_wiki_returns_sidebar_and_pages`](modules/tests.md) - Tests wiki endpoint responses
- [`test_write_site_loader`](modules/tests.md) - Tests site loader generation
- [`test_writes_each_page_and_sidebar`](modules/tests.md) - Tests basic Markdown export
- [`test_writes_readme_landing_page_with_overview_and_contents`](modules/tests.md) - Tests README generation

## Variable

### [repowiki](modules/repowiki.md)

- [`MODEL_ALIASES`](modules/repowiki.md) - Dictionary mapping common model shortcuts to full identifiers.
- [`MODEL_API_BASES`](modules/repowiki.md) - Maps specific model strings to their API base URLs for OpenAI-compatible vendors.
- [`__version__`](modules/repowiki.md) - Current version of the repowiki package.

## Configuration

### [frontend](modules/frontend.md)

- [`build.outDir`](modules/frontend.md) - Specifies the output directory for built files (../src/repowiki/server/static).
- [`compilerOptions`](modules/frontend.md) - Sets TypeScript options like target (ES2020), module resolution (bundler), JSX (react-jsx), and strict type checking.
- [`dependencies`](modules/frontend.md) - Lists runtime dependencies including React, React Router, Mermaid for diagrams, Shiki for syntax highlighting, and Zustand for state management.
- [`devDependencies`](modules/frontend.md) - Lists development dependencies including Vite, TypeScript, Tailwind CSS, and related plugins.
- [`scripts`](modules/frontend.md) - Defines npm scripts for development (dev), building (build), and previewing (preview) the application.
- [`server.proxy`](modules/frontend.md) - Proxies API requests to the backend server running on localhost:8000.

## Component

### [frontend](modules/frontend.md)

- [`App`](modules/frontend.md) - Main application component that renders BrowserRouter and defines routes for Home, WikiView, ChatView, and FileView.
- [`ChatView`](modules/frontend.md) - Displays chat messages, handles user input, streams AI responses, and shows source code references.
- [`FileView`](modules/frontend.md) - Fetches and displays a source file with syntax highlighting using Shiki, supports line highlighting via URL hash.
- [`Home`](modules/frontend.md) - Displays project description, URL input field, scan progress, and settings modal.
- [`MermaidDiagram`](modules/frontend.md) - Component that takes Mermaid code as input, renders it to SVG using the Mermaid library, and displays errors if rendering fails.
- [`Routes`](modules/frontend.md) - Defines route paths and their corresponding components.
- [`SettingsModal`](modules/frontend.md) - Displays form inputs for API key, model selection, and language selection, with changes persisted to the Zustand store and localStorage.
- [`WikiContent`](modules/frontend.md) - Component that splits content into text and Mermaid parts, renders Mermaid diagrams separately, and converts markdown text to HTML with Tailwind CSS styling.
- [`WikiSidebar`](modules/frontend.md) - Renders a collapsible sidebar with project name, hierarchical page navigation, and a button to open the chat view.
- [`WikiView`](modules/frontend.md) - Fetches wiki structure and page content, renders WikiSidebar and WikiContent components.

## Element

### [frontend](modules/frontend.md)

- [`root`](modules/frontend.md) - Div element where the React app is mounted.

## Hook

### [frontend](modules/frontend.md)

- [`useEffect`](modules/frontend.md) - Used to load wiki structure and page content when the project ID or current page ID changes.
- [`useWikiStore`](modules/frontend.md) - Accesses and updates settings from the global state store.

## Interface

### [frontend](modules/frontend.md)

- [`SidebarItem`](modules/frontend.md) - Defines the structure of sidebar items including title, page_id, and optional children for nested pages.

## Object

### [frontend](modules/frontend.md)

- [`LANG_ALIAS`](modules/frontend.md) - Maps language names from the scanner to Shiki grammar IDs for syntax highlighting.

## Store

### [frontend](modules/frontend.md)

- [`useWikiStore`](modules/frontend.md) - Zustand store with persisted state for project ID, project info, wiki data, current page, scan progress, chat messages, loading states, errors, and settings.

## Middleware

### [frontend](modules/frontend.md)

- [`persist`](modules/frontend.md) - Persists parts of the store (projectId and settings) to sessionStorage.

## Directive

### [frontend](modules/frontend.md)

- [`reference types`](modules/frontend.md) - References Vite client types for module resolution.

## Environment_variable

### [root](modules/root.md)

- [`ANTHROPIC_API_KEY`](modules/root.md) - API key for Anthropic LLM provider
- [`DEEPSEEK_API_KEY`](modules/root.md) - API key for DeepSeek LLM provider
- [`OPENAI_API_KEY`](modules/root.md) - API key for OpenAI LLM provider
- [`REPOWIKI_LANG`](modules/root.md) - Output language for documentation (en, zh, ja, ko)
- [`REPOWIKI_MODEL`](modules/root.md) - Default LLM model to use (optional)

## Package

### [root](modules/root.md)

- [`repowiki`](modules/root.md) - Main package name and entry point configuration

## Script

### [root](modules/root.md)

- [`cli`](modules/root.md) - Command-line interface entry point

## Dependency_group

### [root](modules/root.md)

- [`web`](modules/root.md) - Optional dependencies for web server functionality

## Job

### [.github](modules/.github.md)

- [`demo`](modules/.github.md) - Installs the project, generates a wiki from the repository, and publishes it to the gh-pages branch.
- [`frontend`](modules/.github.md) - Builds the frontend using Node.js to ensure the UI compiles correctly.
- [`lint-and-test`](modules/.github.md) - Executes linting and testing across multiple OSes and Python versions using ruff and pytest.
- [`publish`](modules/.github.md) - Builds the frontend, creates a wheel package, verifies its contents, and publishes it to PyPI.
- [`rag-eval`](modules/.github.md) - Runs retrieval evaluation tests as a non-blocking check to detect regressions.
- [`wheel`](modules/.github.md) - Builds a wheel package and verifies it includes the built frontend files.
