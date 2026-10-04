# tests

> Unit tests for the repowiki codebase, covering core functionality like AI analysis, caching, RAG, and exports.

The tests module verifies the behavior of repowiki's components, including the analyzer, cache, chat system, graph dependencies, and export formats. It uses pytest fixtures and async tests to simulate real-world scenarios, ensuring reliability and correctness across the codebase.

## Files

### `tests/test_analyzer_guide.py`

Tests the reading guide generation, caching, and error handling in the analyzer.

- `test_reading_guide_ranks_by_pagerank_not_scan_order` (function) - Ensures the reading guide ranks files by PageRank instead of scan order.
- `StubLLM` (class) - Mocks LLM calls for testing, recording inputs and returning canned JSON.

### `tests/test_cache.py`

Tests the content-addressed LLM cache for persistence, TTL, and reuse.

- `test_module_analysis_reuses_cache_on_second_run` (function) - Verifies that module analysis reuses cached results on subsequent runs.
- `Cache` (class) - Manages a SQLite-based cache for LLM responses and project data.

### `tests/test_chat_prompt.py`

Tests multi-turn chat prompt building and CLI integration.

- `build_chat_prompt` (function) - Constructs a chat prompt with history, capping turns and filtering malformed messages.
- `test_history_threads_before_the_question_in_order` (function) - Ensures chat history is threaded correctly into the prompt.

### `tests/test_chat_router.py`

Tests the FastAPI chat router's history threading and response streaming.

- `test_chat_router_threads_history_into_prompt` (function) - Checks that the router includes conversation history in LLM prompts.
- `StubLLM` (class) - Mocks LLM streaming for testing chat endpoints.

### `tests/test_config.py`

Tests model aliases, vendor endpoints, and configuration loading.

- `resolve_model` (function) - Resolves shorthand model names to full vendor-specific identifiers.
- `Config` (class) - Handles configuration loading from environment variables and files.

### `tests/test_cross_links.py`

Tests cross-reference linking between symbols and files in the wiki.

- `test_known_symbol_mention_becomes_a_link` (function) - Ensures symbol mentions in markdown are converted to clickable links.

### `tests/test_diff.py`

Tests the diff command for ranking changed files by impact.

- `test_report_ranks_changed_files_by_pagerank_and_blast_radius` (function) - Verifies that diff reports prioritize files by dependency impact.

### `tests/test_github_token.py`

Tests GitHub token handling for private repository ingestion.

- `test_token_used_for_github_clone` (function) - Checks that tokens are used to authenticate GitHub clones.
- `test_token_never_leaks_into_errors` (function) - Ensures tokens are redacted from error messages.

### `tests/test_graph.py`

Tests dependency graph construction, cycle detection, and entry point analysis.

- `DependencyGraph` (class) - Builds and analyzes file dependencies from import statements.
- `test_find_circular_dependencies_detects_mutual_imports` (function) - Verifies that circular dependencies are correctly identified.

### `tests/test_html_export.py`

Tests the self-contained HTML wiki export functionality.

- `export_html` (function) - Exports a wiki to a single HTML file with navigation.
- `test_html_export_skips_the_write_when_content_is_unchanged` (function) - Ensures HTML export avoids redundant writes if content is unchanged.

### `tests/test_incremental.py`

Tests incremental wiki regeneration to skip unchanged pages.

- `test_second_run_with_no_changes_skips_everything` (function) - Checks that no LLM calls or writes occur if no files change.
- `StubLLM` (class) - Mocks LLM for tracking calls during incremental tests.

### `tests/test_knowledge_cards.py`

Tests the generation of knowledge cards for module overviews.

- `test_cards_page_lists_one_card_per_module` (function) - Verifies that each module gets a compact card in the overview.

### `tests/test_lazy_litellm.py`

Ensures litellm is lazily imported to avoid startup costs.

- `test_package_cli_and_analyzer_imports_stay_litellm_free` (function) - Checks that CLI and analyzer imports do not load litellm prematurely.

### `tests/test_llm_retry.py`

Tests LLM client retry logic for transient and fatal errors.

- `LLMClient` (class) - Handles LLM calls with retries and error handling.
- `test_transient_error_retries_until_success` (function) - Ensures transient errors trigger retries until success.

### `tests/test_markdown_export.py`

Tests Markdown wiki export, including README generation.

- `export_markdown` (function) - Exports wiki to Markdown files with a README landing page.
- `test_writes_readme_landing_page_with_overview_and_contents` (function) - Checks that README includes overview and sidebar contents.

### `tests/test_rag.py`

Tests TF-IDF retrieval for the chat system.

- `test_retrieve_ranks_relevant_file_first` (function) - Ensures RAG retrieves the most relevant file for a query.
- `SimpleRAG` (class) - Implements TF-IDF-based retrieval for code chunks.

### `tests/test_rag_eval.py`

Runs retrieval evaluation suite to maintain baseline performance.

- `test_fixture_suite_holds_baseline` (function) - Verifies that RAG performance meets the recorded baseline.

### `tests/test_rag_persistence.py`

Tests on-disk RAG index persistence and invalidation.

- `test_index_round_trip` (function) - Checks that the RAG index can be saved and reloaded.

### `tests/test_repo_map.py`

Tests the repo map command for dependency-based ranking.

- `test_map_json_ranks_by_dependency_pagerank` (function) - Ensures map output ranks files by PageRank scores.

### `tests/test_scan_report.py`

Tests scan coverage reporting for partial and full scans.

- `ScanReport` (class) - Tracks file coverage, oversized files, and skipped directories.
- `test_report_counts_oversized_files_with_example_paths` (function) - Verifies that oversized files are reported with paths.

### `tests/test_scan_wiki_routers.py`

Tests FastAPI routers for scan and wiki endpoints.

- `test_scan_registers_project_and_background_task_runs` (function) - Checks that scan endpoints register projects and trigger background tasks.

### `tests/test_scanner.py`

Tests directory scanning with ignore rules and file prioritization.

- `scan_directory` (function) - Scans a directory for code files, applying ignores and size limits.
- `test_scan_skips_minified_suffixes` (function) - Ensures minified files like .min.js are skipped.

### `tests/test_server_static.py`

Tests static file serving and client-side routing fallbacks.

- `test_root_serves_built_frontend` (function) - Checks that the root URL serves the frontend index.html.

### `tests/test_site_and_serve.py`

Tests the serve command and site loader generation.

- `write_site_loader` (function) - Generates a static site loader for GitHub Pages.

### `tests/test_skeleton.py`

Tests symbol skeleton extraction for oversized Python files.

- `python_skeleton` (function) - Extracts class and function signatures from Python code, truncating if needed.
- `context_for_file` (function) - Returns full content for small files or a skeleton for large Python files.

### `tests/test_smoke.py`

Smoke tests to catch import errors in public modules.

- `test_package_imports` (function) - Imports the main package to verify no ImportError.

### `tests/test_symbol_index.py`

Tests the symbol index page generation and linking.

- `test_kind_sections_follow_first_appearance_order` (function) - Ensures symbol kinds are grouped in the order they first appear.

## Key Concepts

- **StubLLM**: A mock LLM class used across tests to simulate AI responses without real API calls, recording inputs for verification.
- **PageRank**: Algorithm used to rank files by dependency importance, tested in map and diff commands.
- **Incremental Regeneration**: Feature that skips re-generating unchanged wiki pages, tested for efficiency and correctness.
- **RAG (Retrieval-Augmented Generation)**: TF-IDF-based system for retrieving relevant code chunks during chat, tested for accuracy and persistence.

## Internal Relationships

- `tests/test_analyzer_guide.py` → `tests/test_cache.py`: Uses StubLLM and cache to test analyzer behavior.
- `tests/test_chat_prompt.py` → `tests/test_chat_router.py`: Both test chat functionality, with prompt building and router endpoints.
- `tests/test_incremental.py` → `tests/test_cache.py`: Relies on cache for testing incremental regeneration.
- `tests/test_rag.py` → `tests/test_rag_eval.py`: RAG tests are validated against the eval suite for performance.
- `tests/test_scan_report.py` → `tests/test_scanner.py`: Scan report tests use the scanner to generate coverage data.
