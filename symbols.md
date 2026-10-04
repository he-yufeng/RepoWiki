# Symbol Index

94 symbols across 5 modules.

## Function

### [evals](modules/evals.md)

- [`print_report`](modules/evals.md) - Displays evaluation results comparing against baseline
- [`run_eval`](modules/evals.md) - Executes the evaluation and returns accuracy results

### [frontend](modules/frontend.md)

- [`createRoot`](modules/frontend.md) - Renders the App component into the root DOM element.
- [`defineConfig`](modules/frontend.md) - Defines Vite configuration with plugins, server proxy for API calls, and build output directory.
- [`getFileContent`](modules/frontend.md) - Fetches file content for source code viewing.
- [`getPage`](modules/frontend.md) - Retrieves content for a specific wiki page.
- [`getWiki`](modules/frontend.md) - Fetches the wiki structure for a project.
- [`markdownToHtml`](modules/frontend.md) - Converts Markdown syntax to HTML with custom styling.
- [`scanProject`](modules/frontend.md) - Initiates a project scan by sending a request to the backend.
- [`splitMermaid`](modules/frontend.md) - Splits content into text and Mermaid diagram sections for separate rendering.
- [`streamChat`](modules/frontend.md) - Streams chat responses from the AI model with real-time updates.
- [`streamScanProgress`](modules/frontend.md) - Sets up an EventSource to stream real-time scan progress updates.

### [tests](modules/tests.md)

- [`build_chat_prompt`](modules/tests.md) - Constructs a chat prompt with history, capping turns and filtering malformed messages.
- [`context_for_file`](modules/tests.md) - Returns full content for small files or a skeleton for large Python files.
- [`export_html`](modules/tests.md) - Exports a wiki to a single HTML file with navigation.
- [`export_markdown`](modules/tests.md) - Exports wiki to Markdown files with a README landing page.
- [`python_skeleton`](modules/tests.md) - Extracts class and function signatures from Python code, truncating if needed.
- [`resolve_model`](modules/tests.md) - Resolves shorthand model names to full vendor-specific identifiers.
- [`scan_directory`](modules/tests.md) - Scans a directory for code files, applying ignores and size limits.
- [`test_cards_page_lists_one_card_per_module`](modules/tests.md) - Verifies that each module gets a compact card in the overview.
- [`test_chat_router_threads_history_into_prompt`](modules/tests.md) - Checks that the router includes conversation history in LLM prompts.
- [`test_find_circular_dependencies_detects_mutual_imports`](modules/tests.md) - Verifies that circular dependencies are correctly identified.
- [`test_fixture_suite_holds_baseline`](modules/tests.md) - Verifies that RAG performance meets the recorded baseline.
- [`test_history_threads_before_the_question_in_order`](modules/tests.md) - Ensures chat history is threaded correctly into the prompt.
- [`test_html_export_skips_the_write_when_content_is_unchanged`](modules/tests.md) - Ensures HTML export avoids redundant writes if content is unchanged.
- [`test_index_round_trip`](modules/tests.md) - Checks that the RAG index can be saved and reloaded.
- [`test_kind_sections_follow_first_appearance_order`](modules/tests.md) - Ensures symbol kinds are grouped in the order they first appear.
- [`test_known_symbol_mention_becomes_a_link`](modules/tests.md) - Ensures symbol mentions in markdown are converted to clickable links.
- [`test_map_json_ranks_by_dependency_pagerank`](modules/tests.md) - Ensures map output ranks files by PageRank scores.
- [`test_module_analysis_reuses_cache_on_second_run`](modules/tests.md) - Verifies that module analysis reuses cached results on subsequent runs.
- [`test_package_cli_and_analyzer_imports_stay_litellm_free`](modules/tests.md) - Checks that CLI and analyzer imports do not load litellm prematurely.
- [`test_package_imports`](modules/tests.md) - Imports the main package to verify no ImportError.
- [`test_reading_guide_ranks_by_pagerank_not_scan_order`](modules/tests.md) - Ensures the reading guide ranks files by PageRank instead of scan order.
- [`test_report_counts_oversized_files_with_example_paths`](modules/tests.md) - Verifies that oversized files are reported with paths.
- [`test_report_ranks_changed_files_by_pagerank_and_blast_radius`](modules/tests.md) - Verifies that diff reports prioritize files by dependency impact.
- [`test_retrieve_ranks_relevant_file_first`](modules/tests.md) - Ensures RAG retrieves the most relevant file for a query.
- [`test_root_serves_built_frontend`](modules/tests.md) - Checks that the root URL serves the frontend index.html.
- [`test_scan_registers_project_and_background_task_runs`](modules/tests.md) - Checks that scan endpoints register projects and trigger background tasks.
- [`test_scan_skips_minified_suffixes`](modules/tests.md) - Ensures minified files like .min.js are skipped.
- [`test_second_run_with_no_changes_skips_everything`](modules/tests.md) - Checks that no LLM calls or writes occur if no files change.
- [`test_token_never_leaks_into_errors`](modules/tests.md) - Ensures tokens are redacted from error messages.
- [`test_token_used_for_github_clone`](modules/tests.md) - Checks that tokens are used to authenticate GitHub clones.
- [`test_transient_error_retries_until_success`](modules/tests.md) - Ensures transient errors trigger retries until success.
- [`test_writes_readme_landing_page_with_overview_and_contents`](modules/tests.md) - Checks that README includes overview and sidebar contents.
- [`write_site_loader`](modules/tests.md) - Generates a static site loader for GitHub Pages.

## Class

### [evals](modules/evals.md)

- [`CaseResult`](modules/evals.md) - Represents the result of a single question evaluation
- [`EvalReport`](modules/evals.md) - Stores and calculates evaluation metrics

### [tests](modules/tests.md)

- [`Cache`](modules/tests.md) - Manages a SQLite-based cache for LLM responses and project data.
- [`Config`](modules/tests.md) - Handles configuration loading from environment variables and files.
- [`DependencyGraph`](modules/tests.md) - Builds and analyzes file dependencies from import statements.
- [`LLMClient`](modules/tests.md) - Handles LLM calls with retries and error handling.
- [`ScanReport`](modules/tests.md) - Tracks file coverage, oversized files, and skipped directories.
- [`SimpleRAG`](modules/tests.md) - Implements TF-IDF-based retrieval for code chunks.
- [`StubLLM`](modules/tests.md) - Mocks LLM calls for testing, recording inputs and returning canned JSON.

## Configuration

### [frontend](modules/frontend.md)

- [`compilerOptions`](modules/frontend.md) - Sets TypeScript compilation settings including target ES2020, React JSX support, and strict type checking.
- [`dependencies`](modules/frontend.md) - Lists runtime dependencies including React, React Router, Mermaid for diagrams, Shiki for syntax highlighting, and Zustand for state management.
- [`devDependencies`](modules/frontend.md) - Lists development dependencies including Vite, TypeScript, Tailwind CSS, and React plugins.
- [`scripts`](modules/frontend.md) - Defines build and development commands for the application.

## Component

### [frontend](modules/frontend.md)

- [`App`](modules/frontend.md) - Root component that renders the router and defines routes for Home, WikiView, ChatView, and FileView.
- [`ChatView`](modules/frontend.md) - Component that renders the chat interface with message history and input.
- [`FileView`](modules/frontend.md) - Component that renders file content with syntax highlighting and line reference support.
- [`Home`](modules/frontend.md) - Component that renders the main input interface and handles project scanning initiation.
- [`MermaidDiagram`](modules/frontend.md) - Component that renders Mermaid diagrams and handles rendering errors.
- [`SettingsModal`](modules/frontend.md) - Modal component for managing application settings including API keys and AI model selection.
- [`WikiContent`](modules/frontend.md) - Component that parses and renders wiki content with Markdown formatting and embedded diagrams.
- [`WikiSidebar`](modules/frontend.md) - Component that displays the hierarchical navigation structure of wiki pages.
- [`WikiView`](modules/frontend.md) - Component that renders the wiki interface with sidebar and content areas.

## Element

### [frontend](modules/frontend.md)

- [`root`](modules/frontend.md) - The div element where the React application is mounted.

## Directive

### [frontend](modules/frontend.md)

- [`@import`](modules/frontend.md) - Imports Tailwind CSS framework for styling.

## Store

### [frontend](modules/frontend.md)

- [`useWikiStore`](modules/frontend.md) - Zustand store that manages project data, wiki content, chat messages, settings, and application state.

## Environment_variable

### [root](modules/root.md)

- [`ANTHROPIC_API_KEY`](modules/root.md) - API key for Anthropic LLM provider.
- [`DEEPSEEK_API_KEY`](modules/root.md) - API key for DeepSeek LLM provider.
- [`OPENAI_API_KEY`](modules/root.md) - API key for OpenAI LLM provider.
- [`REPOWIKI_LANG`](modules/root.md) - Output language for documentation (en, zh, ja, ko).
- [`REPOWIKI_MODEL`](modules/root.md) - Default LLM model to use (e.g., deepseek/deepseek-chat).

## Cli_command

### [root](modules/root.md)

- [`repowiki chat`](modules/root.md) - Command for interactive terminal Q&A about the codebase.
- [`repowiki scan`](modules/root.md) - Command to scan a codebase and generate wiki documentation.
- [`repowiki serve`](modules/root.md) - Command to start the web interface for browsing documentation.

## Python_package

### [root](modules/root.md)

- [`repowiki`](modules/root.md) - Main package entry point defined in project.scripts.

## Dependency

### [root](modules/root.md)

- [`fastapi`](modules/root.md) - Web framework for the optional web interface.
- [`litellm`](modules/root.md) - LLM orchestration library for API calls.

## Job

### [.github](modules/.github.md)

- [`demo`](modules/.github.md) - Installs repowiki, scans the repository, and publishes the generated wiki site to gh-pages branch.
- [`frontend`](modules/.github.md) - Builds the frontend using Node.js to ensure UI components compile correctly.
- [`lint-and-test`](modules/.github.md) - Runs ruff linter and pytest suite on multiple OSes and Python versions.
- [`publish`](modules/.github.md) - Builds frontend, constructs Python package, verifies wheel contents, and publishes to PyPI.
- [`rag-eval`](modules/.github.md) - Executes retrieval evaluation tests (non-blocking) to detect regressions.
- [`wheel`](modules/.github.md) - Validates that the built wheel includes the frontend static files for serving.

## Field

### [evals](modules/evals.md)

- [`boosted`](modules/evals.md) - Enhanced accuracy scores using improved retrieval methods
- [`expect_files`](modules/evals.md) - Expected correct source file paths for the answer
- [`overall`](modules/evals.md) - Overall accuracy score across all repositories
- [`question`](modules/evals.md) - The question text asking about code functionality
- [`repo`](modules/evals.md) - Which repository the question targets
- [`repos`](modules/evals.md) - Individual repository accuracy scores
- [`tier`](modules/evals.md) - Question difficulty level (paraphrase questions use different wording)
